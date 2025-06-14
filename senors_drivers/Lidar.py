# -- coding: utf-8 --
import pigpio
import serial
from time import sleep

def get_sector_label(angle):
    if 0 <= angle <= 60:
        return "North East"
    elif 61 <= angle <= 120:
        return "North"
    elif 121 <= angle <= 180:
        return "North West"
    else:
        return "Unknown"

class TfMiniSweepScanner:
    def __init__(self,
                 servo_pin=18,
                 serial_port='/dev/serial0',
                 baud_rate=115200,
                 angle_step=2,
                 servo_min_pulse=1000,
                 servo_max_pulse=2000,
                 servo_min_angle=0,
                 servo_max_angle=180,
                 servo_move_delay=0.015,
                 read_delay=0.01):

        self.servo_pin = servo_pin
        self.angle_step = angle_step
        self.servo_min_pulse = servo_min_pulse
        self.servo_max_pulse = servo_max_pulse
        self.servo_min_angle = servo_min_angle
        self.servo_max_angle = servo_max_angle
        self.servo_move_delay = servo_move_delay
        self.read_delay = read_delay

        self.last_valid_distance = None
        self.last_valid_strength = None

        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise IOError("Could not connect to pigpio daemon!")

        try:
            self.tf_serial = serial.Serial(serial_port, baud_rate, timeout=0.1)
        except serial.SerialException as e:
            self.pi.stop()
            raise IOError(f"Failed to connect to TFMini-Plus: {e}")

    def angle_to_pulsewidth(self, angle):
        pulse = self.servo_min_pulse + (angle - self.servo_min_angle) / \
                (self.servo_max_angle - self.servo_min_angle) * \
                (self.servo_max_pulse - self.servo_min_pulse)
        return int(pulse)

    def read_distance(self):
        data = self.tf_serial.read(9)
        if len(data) == 9 and data[0] == 0x59 and data[1] == 0x59:
            distance = data[2] + data[3] * 256
            strength = data[4] + data[5] * 256
            return distance, strength
        return None, None

    def move_and_measure(self, angle, return_data=False):
        pulsewidth = self.angle_to_pulsewidth(angle)
        self.pi.set_servo_pulsewidth(self.servo_pin, pulsewidth)
        sleep(self.servo_move_delay)

        self.tf_serial.reset_input_buffer()
        sleep(self.read_delay)
        distance, strength = self.read_distance()

        sector = get_sector_label(angle)

        if distance == 0:
            distance = None

        if distance is not None:
            self.last_valid_distance = distance
            self.last_valid_strength = strength

        if self.last_valid_distance is not None:
            if self.last_valid_distance == 0:
                print(f"{sector} | Angle {angle} Distance: Out of Range, Strength: {self.last_valid_strength}")
            else:
                print(f"{sector} | Angle {angle} Distance: {self.last_valid_distance} cm, Strength: {self.last_valid_strength}")
        else:
            print(f"{sector} | Angle {angle} Distance: N/A, Strength: N/A")

        if return_data:
            return angle, self.last_valid_distance, self.last_valid_strength, sector

    def sweep_loop(self):
        print("Starting single sweep collection...\n")
        sweep_data = []

        try:
            # Forward sweep
            for angle in range(self.servo_min_angle, self.servo_max_angle + 1, self.angle_step):
                result = self.move_and_measure(angle, return_data=True)
                if result:
                    sweep_data.append(result)

            # Backward sweep
            for angle in range(self.servo_max_angle, self.servo_min_angle - 1, -self.angle_step):
                result = self.move_and_measure(angle, return_data=True)
                if result:
                    sweep_data.append(result)

            print("\nFull Sweep Data (angle, distance, strength, sector):")
            for entry in sweep_data:
                print(entry)

        except KeyboardInterrupt:
            print("Sweep stopped by user.")

    def stop(self):
        self.pi.set_servo_pulsewidth(self.servo_pin, 0)
        self.pi.stop()
        self.tf_serial.close()

if __name__ == "__main__":
    scanner = None
    try:
        scanner = TfMiniSweepScanner()
        scanner.sweep_loop()
    finally:
        if scanner:
            scanner.stop()
