import serial
import time
import pyrebase
import pandas as pd
import os

# Serial port configuration for TFmini Plus
ser = serial.Serial("/dev/serial0", 115200, timeout=1)

# firebase Configuration
config = {
  "apiKey": "IYrIkDHqG9bnGgOTiDdTxTsZCFR0JCkO2HsFsZXa",
  "authDomain": "sea-eyes.firebaseapp.com",
  "databaseURL": "https://sea-eyes-default-rtdb.europe-west1.firebasedatabase.app",
  "storageBucket": "sea-eyes.appspot.com"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# Initialize Excel file path
excel_file = "tfmini_readings.xlsx"

# Create DataFrame to hold the data
if os.path.exists(excel_file):
    df = pd.read_excel(excel_file)
else:
    df = pd.DataFrame(columns=["Timestamp", "Distance_cm", "Strength"])

# Function to get TFmini Plus data and publish it to Firebase + log to Excel
def getTFminiData():
    global df

    count = ser.in_waiting
    if count > 8:
        recv = ser.read(9)
        ser.reset_input_buffer()

        if recv[0] == 0x59 and recv[1] == 0x59:
            distance = recv[2] + recv[3] * 256
            strength = recv[4] + recv[5] * 256
            timestamp = time.time()

            print(f"Distance: {distance} cm, Strength: {strength}")

            # Prepare MQTT payload
            payload = {
                "distance_ld": distance,
                "strength": strength,
                "timestamp": timestamp
            }

            # Publish data to Firebase
            db.child("ultra_sonic").child("4-set").set(payload)

            # Add to DataFrame
            new_row = {"Timestamp": timestamp, "Distance_cm": distance, "Strength": strength}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            # Save to Excel
            df.to_excel(excel_file, index=False)

            # Delay
            time.sleep(0.5)

# Start data collection loop
try:
    while True:
        getTFminiData()
except KeyboardInterrupt:
    print("Exiting and saving data...")

