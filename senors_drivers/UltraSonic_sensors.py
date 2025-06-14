import RPi.GPIO as GPIO
import time
import threading
import pyrebase

# Constants
TRIG_PIN = 27
ECHO_PINS = [2, 3, 4, 17]
POSITIONS = ["Top left", "Top right", "Bottom left", "Bottom right"]
MIN_DISTANCE = 2.0     # cm
MAX_DISTANCE = 400.0   # cm

# Firebase setup
config = {
    "apiKey": "IYrIkDHqG9bnGgOTiDdTxTsZCFR0JCkO2HsFsZXa",
    "authDomain": "sea-eyes.firebaseapp.com",
    "databaseURL": "https://sea-eyes-default-rtdb.europe-west1.firebasedatabase.app",
    "storageBucket": "sea-eyes.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.output(TRIG_PIN, False)
time.sleep(0.1)  # Allow GPIO to settle

for pin in ECHO_PINS:
    GPIO.setup(pin, GPIO.IN)

# Shared variables
distances = {}
trigger_lock = threading.Lock()

# Ultrasonic sensor thread function
def ultrasonic_worker(echo_pin, position):
    global distances
    while True:
        with trigger_lock:
            GPIO.output(TRIG_PIN, True)
            time.sleep(0.00001)
            GPIO.output(TRIG_PIN, False)

        timeout = time.time() + 0.1
        while GPIO.input(echo_pin) == 0:
            if time.time() > timeout:
                distances[position] = MAX_DISTANCE
                # print(f"[{position}] Timeout waiting for echo start → {MAX_DISTANCE} cm")
                break
        else:
            start = time.time()
            while GPIO.input(echo_pin) == 1:
                if time.time() - start > 0.1:
                    distances[position] = MAX_DISTANCE
                    #print(f"[{position}] Timeout waiting for echo end → {MAX_DISTANCE} cm")
                    break
            else:
                duration = time.time() - start
                distance = (duration * 34300) / 2

                if distance < MIN_DISTANCE:
                    distance = MIN_DISTANCE
                    #print(f"[{position}] Very close object → clamped to {MIN_DISTANCE} cm")
                elif distance > MAX_DISTANCE:
                    distance = MAX_DISTANCE
                    #print(f"[{position}] Too far object → clamped to {MAX_DISTANCE} cm")

                distances[position] = round(distance, 2)

        time.sleep(1)  # Wait 1 second before next reading

# Start threads
try:
    for i in range(4):
        t = threading.Thread(target=ultrasonic_worker, args=(ECHO_PINS[i], POSITIONS[i]))
        t.daemon = True
        t.start()
        time.sleep(0.2)  # stagger thread starts

    while True:
        if len(distances) == 4:
            for k, v in distances.items():
                print(f"{k}: {v} cm")
            print('-' * 30)
            db.child("ultra_sonic").child("1-set").set(distances)
        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting...")
    GPIO.cleanup()
