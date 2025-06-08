
import os
import sys
import argparse
import glob
import time
import datetime
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from openpyxl import Workbook

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True, help='Path to YOLO model file (e.g. yolo11s.pt)')
parser.add_argument('--source', required=True, help='Image, folder, video file, USB index, or stream URL')
parser.add_argument('--thresh', default=0.5, type=float, help='Confidence threshold')
parser.add_argument('--resolution', default=None, help='Resolution WxH (e.g. 640x480)')
parser.add_argument('--record', action='store_true', help='Record video (requires --resolution)')
args = parser.parse_args()

model_path = args.model
img_source = args.source
min_thresh = args.thresh
record = args.record
resize = False

if args.resolution:
    resize = True
    resW, resH = map(int, args.resolution.split('x'))

device = 'cuda' if torch.cuda.is_available() else 'cpu'

if not os.path.exists(model_path):
    print("Model file not found.")
    sys.exit(1)

model = YOLO(model_path)
labels = model.names
print(f"Loaded YOLO model: {model_path}")

scaling_factors = {
    'person': 2.5, 'car': 3.0, 'truck': 3.5, 'bicycle': 2.8, 'motorcycle': 2.8,
    'bus': 4.0, 'train': 4.5, 'boat': 3.5, 'traffic light': 5.0,
    'Buoy': 1.8, 'Cruise_ship': 6.0, 'Ferry_boat': 5.0, 'Freight_boat': 5.5,
    'Gondola': 2.5, 'Inflitable_boat': 2.0, 'Kayak': 1.5, 'Paper_boat': 0.8,
    'Sailboat': 3.0,
}

midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
midas.to(device).eval()
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
transform = midas_transforms.small_transform
print("Loaded MiDaS_small depth model")

img_exts = ['.jpg', '.jpeg', '.png', '.bmp']
vid_exts = ['.avi', '.mp4', '.mov', '.mkv', '.wmv']
source_type = None

if os.path.isdir(img_source):
    source_type = 'folder'
elif os.path.isfile(img_source):
    _, ext = os.path.splitext(img_source)
    source_type = 'image' if ext in img_exts else 'video' if ext in vid_exts else None
elif img_source.startswith('usb'):
    source_type = 'usb'
    usb_idx = int(img_source[3:])
elif img_source.startswith('http://') or img_source.startswith('https://'):
    source_type = 'http'
else:
    print(f"Unsupported source: {img_source}")
    sys.exit(1)

if source_type == 'image':
    imgs_list = [img_source]
elif source_type == 'folder':
    imgs_list = [f for f in glob.glob(img_source + "/*") if os.path.splitext(f)[1] in img_exts]
elif source_type in ['video', 'usb', 'http']:
    cap = cv2.VideoCapture(img_source if source_type != 'usb' else usb_idx)
    if resize:
        cap.set(3, resW)
        cap.set(4, resH)
    if not cap.isOpened():
        print("Failed to open video stream.")
        sys.exit(1)
    if record:
        if not resize:
            print("Recording requires --resolution.")
            sys.exit(1)
        out = cv2.VideoWriter("recorded_output.avi", cv2.VideoWriter_fourcc(*'XVID'), 30, (resW, resH))

excel_wb = Workbook()
excel_ws = excel_wb.active
excel_ws.title = "Distance Readings"
excel_ws.append(["Timestamp", "Class", "Distance_m"])
distance_log_interval = 20

avg_frame_rate = 0
frame_rate_buffer = []
fps_avg_len = 200
img_count = 0
frame_idx = 0
depth_map = None
depth_interval = 30

try:
    while True:
        t_start = time.perf_counter()

        if source_type in ['image', 'folder']:
            if img_count >= len(imgs_list):
                print("Done with images.")
                break
            frame = cv2.imread(imgs_list[img_count])
            img_count += 1
        else:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("End of stream or failed to grab frame.")
                break

        if resize:
            frame = cv2.resize(frame, (resW, resH))

        results = model(frame, verbose=False)
        detections = results[0].boxes

        if frame_idx % depth_interval == 0 or depth_map is None:
            input_midas = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            input_tensor = transform(input_midas).to(device)
            with torch.no_grad():
                prediction = midas(input_tensor)
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=frame.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()
                depth_map = prediction.cpu().numpy()
                min_d, max_d = depth_map.min(), depth_map.max()
                print(f"Depth map min: {min_d:.3f}, max: {max_d:.3f}")
                if max_d - min_d < 1e-5:
                    continue
                normalized_depth_map = (depth_map - min_d) / (max_d - min_d + 1e-6)

        for i in range(len(detections)):
            box = detections[i].xyxy.cpu().numpy().squeeze().astype(int)
            classid = int(detections[i].cls.item())
            conf = detections[i].conf.item()
            if conf < min_thresh:
                continue

            class_name = labels[classid]
            scaling_factor = scaling_factors.get(class_name, 3.0)

            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            if 0 <= cx < depth_map.shape[1] and 0 <= cy < depth_map.shape[0]:
                depth_val = normalized_depth_map[cy, cx]
                depth_val = np.clip(depth_val, 0.05, 1.0)
                distance_m = (1.0 / depth_val) * scaling_factor
                label = f'{class_name} ({distance_m:.2f} m, {int(conf*100)}%)'
                if frame_idx % distance_log_interval == 0:
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    excel_ws.append([timestamp, class_name, distance_m])
            else:
                label = f'{class_name} ({int(conf*100)}%)'

            cv2.rectangle(frame, tuple(box[:2]), tuple(box[2:]), (0, 255, 0), 2)
            cv2.putText(frame, label, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        t_stop = time.perf_counter()
        fps = 1 / (t_stop - t_start)
        frame_rate_buffer.append(fps)
        if len(frame_rate_buffer) > fps_avg_len:
            frame_rate_buffer.pop(0)
        avg_frame_rate = np.mean(frame_rate_buffer)

        cv2.putText(frame, f'FPS: {avg_frame_rate:.2f}', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 0), 2)
        cv2.imshow("YOLO + MiDaS Distance", frame)

        if record:
            out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        frame_idx += 1

except KeyboardInterrupt:
    print("Interrupted by user.")

if source_type in ['video', 'usb', 'http']:
    cap.release()
if record:
    out.release()
cv2.destroyAllWindows()

excel_file_path = "object_detection_midas_log.xlsx"
excel_wb.save(excel_file_path)
print(f"Distances saved to {excel_file_path}")
print(f"Average FPS: {avg_frame_rate:.2f}")
