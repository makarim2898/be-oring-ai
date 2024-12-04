import serial
import time

def test_serial_communication():
    port = '/dev/ttyUSB0'  # Sesuaikan dengan port serial yang terdeteksi
    baudrate = 9600

    # Membuka port serial
    ser = serial.Serial(port, baudrate, timeout=1)
    time.sleep(2)  # Menunggu inisialisasi serial

    # Mengirim data
    ser.write(b'Hello Android!\n')

    # Menerima data
    received_data = ser.readline().decode('utf-8').strip()
    print(f"Data received: {received_data}")

    # Menutup port serial
    ser.close()

if __name__ == "__main__":
    test_serial_communication()
