import serial
import time
import pyrebase
import RPi.GPIO as GPIO
import threading
import pigpio
from time import sleep

from tfmini_scanner import TfMiniSweepScanner


# Firebase config
config = {
    "apiKey": "IYrIkDHqG9bnGgOTiDdTxTsZCFR0JCkO2HsFsZXa",
    "authDomain": "sea-eyes.firebaseapp.com",
    "databaseURL": "https://sea-eyes-default-rtdb.europe-west1.firebasedatabase.app",
    "storageBucket": "sea-eyes.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# GPIO Setup
BUZZER_PIN = 21
TRIG_sonar = 5
ECHO_sonar = 6
THRESHOLD_DISTANCE = 10  # cm

TRIG_PIN = 27
ECHO_PINS = [2, 3, 4, 17]
POSITIONS = ["Top left", "Top right", "Bottom left", "Bottom right"]

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.output(BUZZER_PIN, GPIO.LOW)
GPIO.setup(TRIG_sonar, GPIO.OUT)
GPIO.setup(ECHO_sonar, GPIO.IN)
GPIO.setup(TRIG_PIN, GPIO.OUT)
for pin in ECHO_PINS:
    GPIO.setup(pin, GPIO.IN)

# Thread control
stop_threads = False

# Shared alert state
alert_triggered_by = {
    "TFmini": False,
    "Sonar": False,
    "Top left": False,
    "Top right": False,
    "Bottom left": False,
    "Bottom right": False
}
alert_lock = threading.Lock()

def check_alerts(distance, sensor_name):
    global alert_triggered_by
    with alert_lock:
        alert_triggered_by[sensor_name] = distance is not None and distance < THRESHOLD_DISTANCE

def alert_manager():
    while not stop_threads:
        with alert_lock:
            active_alert = any(alert_triggered_by.values())

        if active_alert:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            print("[BUZZER] Alert active ? buzzer ON.")
        else:
            GPIO.output(BUZZER_PIN, GPIO.LOW)

        time.sleep(0.1)



def GPS():
    ser = serial.Serial("/dev/ttyAMA5", 9600, timeout=1)
    while not stop_threads:
        sentence = ser.readline().decode('utf-8', errors='ignore').strip()

        if sentence.startswith("$GPRMC"):
            parts = sentence.split(',')

            if parts[2] != 'A':
                return None
            #time calculations
            raw_time = parts[1]
            hours, minutes, seconds = raw_time[:2], raw_time[2:4], raw_time[4:6]
            gps_time = f"{hours}:{minutes}:{seconds} UTC"

            #latitude calculations
            lat_raw = float(parts[3])
            lat_dir = parts[4]
            latitude = int(lat_raw / 100) + (lat_raw % 100) / 60 #convertion from degree to decimal
            if lat_dir =='S':
                latitude = -latitude
            
            #longitude calculations
            lon_raw = float(parts[5])
            lon_dir = parts[6]
            longitude = int(lon_raw / 100) + (lon_raw % 100) / 60 #convertion from degree to decimal
            if lon_dir == 'W':
                longitude = -longitude
            
            #speed calculations
            speed_knots = float(parts[7])
            speed_km = speed_knots*1.852
            if speed_knots <= 0.5:
                speed_knots = 0

            GPRMC_data = {
                "time": gps_time,
                "latitude": latitude,
                "longitude": longitude,
                "speed_knots": speed_knots
            }
            print(GPRMC_data)
            db.child("ultra_sonic").child("3-set").set(GPRMC_data)

def sonar():
    while not stop_threads:
        GPIO.output(TRIG_sonar, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_sonar, False)

        start_time, stop_time = time.time(), time.time()

        while GPIO.input(ECHO_sonar) == 0:
            start_time = time.time()
        while GPIO.input(ECHO_sonar) == 1:
            stop_time = time.time()

        elapsed_time = stop_time - start_time
        distance = (elapsed_time * 34300) / 2
        distance = round(distance, 2)

        print(f"[Sonar] Distance: {distance} cm")
        check_alerts(distance, "Sonar")
        db.child("ultra_sonic").child("2-set").set({"distance": distance})
        time.sleep(1)

def measure_distance(pin):
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    timeout = time.time() + 0.01
    while GPIO.input(pin) == 0:
        if time.time() > timeout:
            return None
    start_time = time.time()

    timeout = time.time() + 0.01
    while GPIO.input(pin) == 1:
        if time.time() > timeout:
            return None
    end_time = time.time()

    duration = end_time - start_time
    distance = (duration * 34300) / 2
    return round(distance, 2)

def ultra_sonic():
    while not stop_threads:
        payload = {}
        for i, pin in enumerate(ECHO_PINS):
            distance = measure_distance(pin)
            label = POSITIONS[i]
            payload[label] = distance
            print(f"[{label}] Distance: {distance} cm")
            check_alerts(distance, label)
            time.sleep(0.05)  # Short delay between sensor readings

        db.child("ultra_sonic").child("1-set").set(payload)
        time.sleep(1)

def TFminiServoScannerThread(): 
    scanner = TfMiniSweepScanner()
    try:
        while not stop_threads:
            forward_data_payload = {}

            # Forward sweep 0 -> 180
            for angle in range(scanner.servo_min_angle, scanner.servo_max_angle + 1, scanner.angle_step):
                if stop_threads:
                    break
                data = scanner.move_and_measure(angle, return_data=True)
                if data:
                    angle_val, distance, strength, sector = data
                    
                    # Remap angle to mirrored version for the app
                    mapped_angle = 180 - angle_val
                    
                    #check_alerts(distance, "TFmini")
                    forward_data_payload[str(mapped_angle)] = distance if distance is not None else "Out of Range"

            # Sort keys in correct order for mirrored data (from 180 to 0)
            sorted_payload = {
                k: forward_data_payload[k]
                for k in sorted(forward_data_payload, key=lambda x: int(x), reverse=True)
            }
            db.child("ultra_sonic").child("4-set").child("from 0 to 180").set(sorted_payload)

            # Reset servo to 0 degrees
            scanner.move_and_measure(scanner.servo_min_angle)

    finally:
        scanner.stop()









# Start threads
t_sonar = threading.Thread(target=sonar, daemon=True)
t_ultra = threading.Thread(target=ultra_sonic, daemon=True)
t_alert = threading.Thread(target=alert_manager, daemon=True)
t_GPS = threading.Thread(target=GPS, daemon=True)
t_tfmini = threading.Thread(target=TFminiServoScannerThread, daemon=True)

t_sonar.start()
t_ultra.start()
t_alert.start()
t_GPS.start()
t_tfmini.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting safely...")
    stop_threads = True
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.cleanup()
