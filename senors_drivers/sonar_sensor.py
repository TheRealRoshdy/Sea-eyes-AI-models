import time
import RPi.GPIO as GPIO
import pyrebase

# GPIO Pin Configuration for Ultrasonic Sensor
TRIG = 5
ECHO = 6

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

config = {
  "apiKey": "IYrIkDHqG9bnGgOTiDdTxTsZCFR0JCkO2HsFsZXa",
  "authDomain": "sea-eyes.firebaseapp.com",
  "databaseURL": "https://sea-eyes-default-rtdb.europe-west1.firebasedatabase.app",
  "storageBucket": "sea-eyes.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

def get_distance():
    """Measure distance using the ultrasonic sensor."""
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time, stop_time = time.time(), time.time()

    while GPIO.input(ECHO) == 0:
        start_time = time.time()
    while GPIO.input(ECHO) == 1:
        stop_time = time.time()

    elapsed_time = stop_time - start_time
    distance = (elapsed_time * 34300) / 2  # Convert to cm

    return round(distance, 2)


try:
    while True:
        distance = get_distance()
        print("Distance: {}cm".format(distance))

        data = {"distance": distance}
        db.child("ultra_sonic").child("2-set").set(data)

        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopping...")
    GPIO.cleanup()


