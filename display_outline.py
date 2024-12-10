from flask import Blueprint, Response, request, jsonify
from flask_cors import CORS
import cv2
import os
import pandas as pd
import datetime
import numpy as np
import time
from ultralytics import YOLO

display_outline = Blueprint('display_outline', __name__)
CORS(display_outline)

#definisi variabel global untuk flags
inspectionFlag = False
bearing_detected = False
resetInspectionFlag = True

#definisi variabel global untuk
latest_frame = None

updateData = {'total_judges': 0,
              'sesion_judges': 0,
              'trigger_start': 0,
              'trigger_reset':0,
              'last_judgement': 'NG',
              'img_path' : '',
              'arduino_connected': False,
              }

#load ypur yolo models from
# model_path = "/home/kaizen-ai/Desktop/thrust_bearing_app/python-backend/models/use pretrained/weights/best.pt"
# model = YOLO("./models/yolov10_normal_online.pt")
# model = YOLO("./models/best.pt")
model = YOLO("yolov8n.pt")

# Class names (replace with your custom names)
custom_names = {0: "OK", 
                1: "NG"}  # Update with your actual class IDs and custom names

# Custom colors for each class
custom_colors = {0: (0, 255, 0), 
                 1: (0, 0, 255)}  # Green for Class 1, Red for Class 2

############## function untuk stream frame ke client ################
def stream_video(device):
    global latest_frame, bearing_detected, inspectionFlag, updateData, resetInspectionFlag
    time.sleep(2)

    # Retry mechanism
    max_retry = 5
    retry_count = 0

    cap = cv2.VideoCapture(device)

    while not cap.isOpened() and retry_count < max_retry:
        print(f"Retrying camera connection... attempt {retry_count + 1}")
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

    # frame_width = 480
    # frame_height = 240

    # frame_width = int((frame_height / 9) * 16)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    while True:
        if not cap.isOpened():
            print("Reinitializing camera...")
            cap.release()
            cap = cv2.VideoCapture(device)
            time.sleep(2)
            continue

        ret, frame = cap.read()
        if not ret:
            print("Tidak dapat membaca frame, mencoba ulang...")
            cap.release()
            cap = cv2.VideoCapture(device)
            time.sleep(2)
            continue

        results = model(frame, conf=0.60, max_det=2)

        hitung_yang_ok = 0
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                confidence = box.conf[0]

                if cls_id == 0:
                    hitung_yang_ok += 1

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
        
        # ret, buffer = cv2.imencode('.jpg', annotated_frame)
        annotated_frame = frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        print("flag status", inspectionFlag, resetInspectionFlag)
        
        if inspectionFlag:
            print("Ini didalam if scann")
            for r in results:
                detected_object = len(r.boxes.cls)
                if detected_object and hitung_yang_ok >= 2:
                    bearing_detected = True
                    save_image(annotated_frame, 'GOOD', 'bearing_complete')
                    print(f'Detected object: {detected_object}')
                    latest_frame = frame
                else:
                    bearing_detected = False
                    print('Bearing not completed yet')
                    save_image(annotated_frame, 'NG', 'not_complete')
                    latest_frame = frame
            
            update_data_dict('last_judgement', bearing_detected)
            update_data_dict('sesion_judges', updateData['sesion_judges'] + 1)
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

############# 
def readCameraIndex():
    df = pd.read_csv('cameraConfig.csv')
    idx_cam_1 = df[df['camera_nm'] == 1]['camera_idx'][0]
    id_camera = idx_cam_1
    return id_camera

############################################################# END POINT ####################################################################################
@display_outline.route('/outline/show-video', methods=['GET'])
def home_show_video():
    id_camera = readCameraIndex()
    print(f"====================  {id_camera}  ====================")

    print(f'Settings show video with camera index {id_camera}')
    return Response(stream_video(id_camera), mimetype='multipart/x-mixed-replace; boundary=frame')

@display_outline.route('/outline/last_detections', methods=['GET'])
def home_show_last():
    return Response(last_detection(), mimetype='multipart/x-mixed-replace; boundary=frame')

@display_outline.route('/outline/get-data', methods=['GET'])
def get_data():
    global updateData
    data = updateData
    # print(data['total_judges'])
    # data = {'bearing_detected': bearing_detected}
    return jsonify(data)

@display_outline.route('/outline/start-scan', methods=['GET'])
def startInspection():
    start_inspection()
    return jsonify("sucess starting inspection")