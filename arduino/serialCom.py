import serial
import time

def init_serial_connection():
    global arduino
    while True:
        print("init_serial_connection called")
        try:
            arduino = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.1)  # Initialize the Arduino port with shorter timeout
            if arduino.isOpen():  # Check if the serial port is open
                arduino.close()  # Close the port if it is open
            arduino.open()  # Reopen the serial port
            print("Connection established.")
            break  # Exit the loop if successful
        except serial.SerialException as e:
            print(f"Serial connection error during initialization: {e}")
            print("Waiting for connection...")
            time.sleep(5)  # Wait for 5 seconds before trying again

def main():
    global arduino
    while True:
        try:
            input_data = arduino.readline().strip().decode('utf-8')
            if input_data == "no trigger":
                print("FROM ARDUINO: CAPTURE IMAGE")
            elif input_data == "start_scan":
                print("FROM ARDUINO: STAND BY POSITION")
        except serial.SerialException:
            print("Serial connection error. Waiting for reconnection...")
            arduino.close()
            init_serial_connection()  # Reinitialize the serial connection
        except UnicodeDecodeError:
            print("Error decoding input data.")

if __name__ == '__main__':
    print("Program ready")
    init_serial_connection()  # Initialize the serial connection
    main()
