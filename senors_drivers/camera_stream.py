from flask import Flask, Response
from picamera2 import Picamera2
import io
import time

app = Flask(__name__)

def generate_frames():
    # Initialize the camera
    picam2 = Picamera2()
    # Configure the camera for video capture
    video_config = picam2.create_video_configuration(main={"size": (1280, 720)})
    picam2.configure(video_config)
    picam2.start()

    try:
        while True:
            # Capture a frame
            stream = io.BytesIO()
            picam2.capture_file(stream, format='jpeg')
            stream.seek(0)
            # Yield the frame in the multipart/x-mixed-replace format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + stream.read() + b'\r\n')
            time.sleep(0.1)  # Add a small delay to control the frame rate
    finally:
        picam2.stop()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
