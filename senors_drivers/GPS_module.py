import serial
import time
import pyrebase


# Set up the correct UART5 serial port and baud rate
serial_port = "/dev/ttyAMA5"  # Using UART5
baud_rate = 9600  # Try 4800 or 115200 if needed

config = {
  "apiKey": "IYrIkDHqG9bnGgOTiDdTxTsZCFR0JCkO2HsFsZXa",
  "authDomain": "sea-eyes.firebaseapp.com",
  "databaseURL": "https://sea-eyes-default-rtdb.europe-west1.firebasedatabase.app",
  "storageBucket": "sea-eyes.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()


def get_GPRMC(serial_port, baud_rate):
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

        if line.startswith("$GPRMC"):
            return line

def get_data_GPRMC(sentence):
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

    return {
        "time": gps_time,
        "latitude": latitude,
        "longitude": longitude,
        "speed_knots": speed_knots
    }


        


try:
    while True:
        GPRMC = get_GPRMC(serial_port, baud_rate)
        GPRMC_data = get_data_GPRMC(GPRMC)
        print(GPRMC_data)
        print('-'*30)
        db.child("ultra_sonic").child("3-set").set(GPRMC_data)
        time.sleep(1)
except KeyboardInterrupt:
    print("exit..")
    



