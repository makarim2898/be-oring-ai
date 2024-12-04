from flask import Blueprint, Response, request, jsonify
from flask_cors import CORS
import cv2
import os
import pandas as pd
import datetime
import numpy as np
import time
from ultralytics import YOLO
import serial
import threading
import subprocess

home_bearing = Blueprint('bearing_routes', __name__)
CORS(home_bearing)

#definisi variabel global untuk flags
inspectionFlag = False
bearing_detected = False
resetInspectionFlag = True
detections_enable = False

frameCount = 0 #untuk menghitung frame yang telah di cek
frameLimiter = 10 #batasan maksimal frame yang di cek
frameDelay = 2 #batasan waktu untuk memulai cek NG
frameDelayDone = False
counter_gagal_baca = 0
counter_gagal_connect = 0

#definisi variabel global untuk
latest_frame = None
buffer_frame_NG1 = None
buffer_frame_NG2 = None
buffer_frame_NG3 = None
original_frame = None
frame_simpan = None

updateData = {'total_judges': 0,
              'sesion_judges': 0,
              'trigger_start': 0,
              'trigger_reset':0,
              'last_judgement': 'NG',
              'img_path' : '',
              'arduino_connected': False,
              }

#load ypur yolo models from
model_path = "/home/kaizen-ai/Desktop/thrust_bearing_app/python-backend/models/use pretrained/weights/best.pt"
# model = YOLO("./models/yolov10_normal_online.pt")
# model = YOLO("./models/best.pt")
model = YOLO(model_path)

# Class names (replace with your custom names)
custom_names = {0: "OK", 1: "NG"}  # Update with your actual class IDs and custom names

# Custom colors for each class
custom_colors = {0: (0, 255, 0), 1: (0, 0, 255)}  # Green for Class 1, Red for Class 2


############## function untuk arduino communication #########
def init_serial_connection():
    global arduino
    while True:
        print("init_serial_connection called")
        try:
            arduino = serial.Serial('/dev/arduino', 115200, timeout=0.1)  # Initialize the Arduino port with shorter timeout
            if arduino.isOpen():  # Check if the serial port is open
                arduino.close()  # Close the port if it is open
            arduino.open()  # Reopen the serial port
            print("Connection established.")
            
            #update flag arduino connected
            update_data_dict('arduino_connected', True)
            
            break  # Exit the loop if successful
        except serial.SerialException as e:
            #update flag arduino conection
            update_data_dict('arduino_connected', False)
            
            print(f"Serial connection error during initialization: {e}")
            print("Waiting for connection...")
            time.sleep(5)  # Wait for 5 seconds before trying again

def baca_data_arduino():
    global arduino, inspectionFlag, resetInspectionFlag, latest_frame, frameCount
    while True:
        try:
            input_data = arduino.readline().strip().decode('utf-8')
            if input_data == "start_scan":
                print(f"FROM ARDUINO: {input_data}")
                inspectionFlag = True
                update_data_dict('trigger_start', True)
                break
            elif input_data == "reset_scan":
                print(f"FROM ARDUINO: {input_data}")
                resetInspectionFlag = True
                inspectionFlag = False
                latest_frame = None
                update_data_dict('trigger_reset', True)
                frameCount = 0
                break
            else:
                update_data_dict('trigger_start', False)
                update_data_dict('trigger_reset', False)
                print(f"FROM ARDUINO: {input_data}")
                break
        except serial.SerialException:
            print("Serial connection error. Waiting for reconnection...")
            arduino.close()
            init_serial_connection()  # Reinitialize the serial connection
        except UnicodeDecodeError:
            print("Error decoding input data.")
            
def kirim_data_ke_arduino(data):
    global arduino
    try:
        if arduino.is_open:
            arduino.write(data.encode('utf-8'))
            print(f"Data sent to Arduino: {data}")
        else:
            print("Serial port is not open. Reinitializing connection...")
            init_serial_connection()
            arduino.write(data.encode('utf-8'))
            print(f"Data sent to Arduino: {data}")
    except serial.SerialException as e:
        print(f"Error sending data to Arduino: {e}")
        arduino.close()
        init_serial_connection()  # Reinitialize the serial connection
    except Exception as e:
        print(f"Unexpected error: {e}")
        
stop_event = threading.Event()

def baca_data_arduino_thread():
    while not stop_event.is_set():
        print("Reading arduino serial")
        baca_data_arduino()

def updateVariabelGlobal():
    global inspectionFlag, resetInspectionFlag
    x = inspectionFlag
    y = resetInspectionFlag
    print("#"*500)
    return x, y
# Menginisialisasi thread di luar fungsi stream_video
#========== coba hentikan thread dulu
arduino_thread = threading.Thread(target=baca_data_arduino_thread)
arduino_thread.daemon = True

############## end of function untuk arduino communication #########

############## function untuk stream frame ke client ################
def stream_video(index_kamera_yang_di_pakai):
    global latest_frame, bearing_detected, inspectionFlag, updateData, resetInspectionFlag
    global frameLimiter, frameCount, buffer_frame_NG1, buffer_frame_NG2, buffer_frame_NG3
    global frameDelay, frameDelayDone, counter_gagal_connect, counter_gagal_baca, original_frame, frame_simpan
    time.sleep(2)

    device = read_attched_camera_idx(index_kamera_yang_di_pakai)
    # Retry mechanism
    max_retry = 5
    retry_count = 0

    cap = cv2.VideoCapture(device)

    while not cap.isOpened() and retry_count < max_retry:
        print(f"Retrying camera connection... attempt {retry_count + 1}")
        device = read_attched_camera_idx(index_kamera_yang_di_pakai)
        cap = cv2.VideoCapture(device)
        time.sleep(2)
        retry_count += 1

    if not cap.isOpened():
        # Generate a placeholder frame with error message
        error_frame = np.zeros((500, 800, 3), np.uint8)
        pesan_string = f'''Camera index {device} out of range
                            Silahkan tekan Refresh Camera atau Halaman Web
                            jika masih berlanjut Lepas pasang USB pada Camera
                            jika masih error lambaikan tangan pada kamera'''
        cv2.putText(error_frame, pesan_string, (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        error_frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')

    if not arduino_thread.is_alive():
        arduino_thread.start()

    frame_width = 480
    frame_height = 240

    frame_width = int((frame_height / 9) * 16)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    while True:
        if not cap.isOpened():
            print("Reinitializing camera...")
            counter_gagal_connect += 1
            cap.release()
            device = read_attched_camera_idx(index_kamera_yang_di_pakai)
            cap = cv2.VideoCapture(device)
            time.sleep(2)
            continue
        
        ret, frame = cap.read()
        if not ret:
            print("Tidak dapat membaca frame, mencoba ulang...")
            counter_gagal_baca += 1
            cap.release()
            device = read_attched_camera_idx(index_kamera_yang_di_pakai)
            cap = cv2.VideoCapture(device)
            time.sleep(2)
            continue
        #salin frame asli untuk disimpan saat ng untuk bahan training
        

        if inspectionFlag and resetInspectionFlag:
            original_frame = frame
            results = model(frame, conf=0.60, max_det=2, imgsz=480)

            hitung_yang_ok = 0
            hitung_yang_ng = 0
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0])
                    confidence = box.conf[0]

                    if cls_id == 0:
                        hitung_yang_ok += 1
                    elif cls_id == 1:
                        hitung_yang_ng += 1

                    label = f"{custom_names.get(cls_id, cls_id)}: {confidence:.2f}"
                    color = custom_colors.get(cls_id, (255, 255, 255))

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    label_ymin = max(y1, label_size[1] + 10)
                    cv2.rectangle(frame, (x1, label_ymin - label_size[1] - 10), (x1 + label_size[0], label_ymin + 5), color, cv2.FILLED)
                    cv2.putText(frame, label, (x1, label_ymin - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # frame_width = 1280
        # frame_height = 720
        # annotated_frame = cv2.resize(frame, (int(frame_width * (810 / frame_height)), 810))
        
        annotated_frame = frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()
        print(f"===== gagal baca : {counter_gagal_baca}, ===== gagal connect : {counter_gagal_connect}")
        print("flag status: inspection, resetInspect", inspectionFlag, resetInspectionFlag)
        # baca_data_arduino()
        print(f"^^^^^ ini frame count {frameCount} ^^^^^")
        if inspectionFlag and resetInspectionFlag:
            frameCount += 1

            if frameCount%frameDelay == 0 and not frameDelayDone:
                frameDelayDone = True

            print(f"memulai pengecekan frame ke {frameCount}, batasnya adalah {frameLimiter} frame")
            # for r in results:
            #     detected_object = len(r.boxes.cls)

            #GOOD ketika ada 2 object dan semuanya OK
            if  hitung_yang_ok >= 2 and frameDelayDone:
                latest_frame = frame
                bearing_detected = True
                resetInspectionFlag = False
                inspectionFlag = False
                frameDelayDone = False
                kirim_data_ke_arduino("out_ok")
                save_image(annotated_frame, 'GOOD', 'bearing_complete')
                # print(f'Detected object: {detected_object}')
                update_data_dict('last_judgement', bearing_detected)
                update_data_dict('sesion_judges', updateData['sesion_judges'] + 1)
            
            #NG ketika terdeteksi no bearing dan bearing ok
            elif buffer_frame_NG1 is None and hitung_yang_ok > 0 and hitung_yang_ng > 0 and frameCount%frameLimiter != 0 and frameDelayDone:
                buffer_frame_NG1 = frame
                frame_simpan1 = original_frame

                print("================ ng1 ========================================================") 

            #NG Ketika terdeteksi no_bearing
            elif buffer_frame_NG2 is None and hitung_yang_ng > 0 and frameCount%frameLimiter != 0 and frameDelayDone:
                print("================= ng2 ========================================================")
                buffer_frame_NG2 = frame
                frame_simpan2 = original_frame


            #NG ketika terdeteksi 1 bearing saja
            elif buffer_frame_NG1 is None and hitung_yang_ok == 1 and frameCount%frameLimiter != 0 and frameDelayDone: 
                buffer_frame_NG3 = frame
                frame_simpan3 = original_frame

                print("================= ng3 ========================================================")

            #salin frame NG ke latest frame
            elif frameCount%frameLimiter == 0:
                kategori = ""
                #salin frame NG ke latest frame berdasar prioritas
                if buffer_frame_NG1:
                    latest_frame = buffer_frame_NG1
                    frame_simpan = frame_simpan1
                    kategori = "NG1"
                elif buffer_frame_NG2:
                    latest_frame = buffer_frame_NG2
                    frame_simpan = frame_simpan2
                    kategori = "NG2"
                elif buffer_frame_NG3 :
                    latest_frame = buffer_frame_NG3
                    frame_simpan = frame_simpan3
                    kategori = "NG3"
                else :
                    latest_frame = frame
                    kategori = "NG4"

                #kosongkan buffer frame untuk next detection
                buffer_frame_NG1 = None
                buffer_frame_NG2 = None
                buffer_frame_NG3 = None

                #setting flag menjadi false agar tidak looping
                bearing_detected = False
                resetInspectionFlag = False
                inspectionFlag = False
                frameDelayDone = False
                
                print('Bearing not completed yet')
                # save_image(frame_simpan, "original", "original_image")
                save_image(frame_simpan, 'NG', f'not_good_{kategori}')
                update_data_dict('last_judgement', bearing_detected)
                update_data_dict('sesion_judges', updateData['sesion_judges'] + 1)
                kirim_data_ke_arduino("out_ng")

            inspectionFlag = False
      
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()
    cv2.destroyAllWindows()


   
############## Function untuk start inspection #################
def start_inspection():
    global inspectionFlag
    inspectionFlag = True
    return 

############## Function untuk save images #################
def save_image(images_to_save, raw_file_name, image_category):
    corrected_name = raw_file_name.replace(' ', '_')

    # Get current date and time for saving the file name.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{corrected_name}_{timestamp}"
    
    # Buat Direktory download
    current_directory = os.path.dirname(os.path.abspath(__file__))
    downloads_directory = os.path.join(current_directory, f'Downloads/{image_category}')
    os.makedirs(downloads_directory, exist_ok=True)
    
    #simpan ke direktori download
    image_path = os.path.join(downloads_directory, f"{file_name}.jpg")  # Menambahkan timestamp pada nama file
    
    cv2.imwrite(image_path, images_to_save)
    print(f"Gambar disimpan di {image_path}")
    
    # Update judgment.csv file with the new data.
    function_update_csv(image_path, file_name)
    return downloads_directory
    

def function_update_csv(pathImg, filename):
    global updateData
    
    df = pd.read_csv("judgement.csv")
    id_terakhir = df['inspection_id'].iloc[-1]
    
    result, date, time= filename.split('_')
    
    id_terakhir += 1
    
    update_data_dict('total_judges', int(id_terakhir))
    
    new_data= {
        "inspection_id" : int(id_terakhir),
        "inspection_date" : int(date),
        "inspection_time" : int(time),
        "inspection_result" : result,
        "image_path" : pathImg
    }
    
    new_row = pd.DataFrame([new_data])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv("judgement.csv", index=False)
    print("Data has been updated in judgement.csv")
    
############## Function untuk menampilkan last detection #################
def last_detection():
    global latest_frame
    while True:
        if latest_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        else:
            # Generate a placeholder frame with a message if no frame is available
            placeholder_frame = np.zeros((500, 800, 3), np.uint8)
            message = "No frame available"
            cv2.putText(placeholder_frame, message, (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', placeholder_frame)
            placeholder_frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder_frame + b'\r\n')
        time.sleep(0.1)  # Add a small delay to avoid high CPU usage

############## Function untuk update data #################
def update_data_dict(key, value):
    global updateData
    updateData[key] = value

############## Function get total judges dari csv file #################
def get_total_judges():
    df = pd.read_csv("judgement.csv")
    id_terakhir = df['inspection_id'].iloc[-1]
    update_data_dict('total_judges', int(id_terakhir))
    
get_total_judges()

############# reading that camera index setting
def readCameraIndex():
    df = pd.read_csv('cameraConfig.csv')
    idx_cam_1 = df[df['camera_nm'] == 1]['camera_idx'][0]
    id_camera = idx_cam_1
    return id_camera

############ function untuk membaca index kamera yang terpasang
def read_attched_camera_idx(index_camera_yang_dimau=0):
    try:
        hasil_check_index = subprocess.check_output("ls /dev/video*", text=True, shell=True)
        array_index = hasil_check_index.strip().split("\n")
        return array_index[index_camera_yang_dimau]
    except subprocess.CalledProcessError:
        print("Tidak ada perangkat kamera yang terdeteksi.")
        return None
    
############################################################# END POINT ####################################################################################
@home_bearing.route('/bearing/show-video', methods=['GET'])
def home_show_video():
    id_camera = readCameraIndex()
    print(f"====================  {id_camera}  ====================")
    init_serial_connection()
    print(f'Settings show video with camera index {id_camera}')
    return Response(stream_video(id_camera), mimetype='multipart/x-mixed-replace; boundary=frame')

@home_bearing.route('/bearing/last_detections', methods=['GET'])
def home_show_last():
    return Response(last_detection(), mimetype='multipart/x-mixed-replace; boundary=frame')

@home_bearing.route('/bearing/get-data', methods=['GET'])
def get_data():
    global bearing_detected
    data = updateData
    print(data['total_judges'])
    # data = {'bearing_detected': bearing_detected}
    return jsonify(data)

@home_bearing.route('/bearing/start', methods=['GET'])
def startInspection():
    start_inspection()
    return "sucess startingspection"