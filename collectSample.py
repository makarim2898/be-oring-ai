from flask import Blueprint, Response, request, jsonify
from flask_cors import CORS
import Home_page as hptb
import time
import cv2
import pandas as pd
import numpy as np
import os

collectSample = Blueprint('collectSample_routes', __name__)
CORS(collectSample)

################################ inisialisasi variabel dan flag #################################
global scanTrigger, resetTrigger, saveFlag
last_frame = None
global saved_frame
saved_frame = None
################################ show videos live #################################
def stream_video(device):
    global last_frame
    time.sleep(2)
    cap = cv2.VideoCapture(device)
    time.sleep(2)
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
    
    # if not hptb.arduino_thread.is_alive():
    #     hptb.arduino_thread.start()
    # Set frame width and height for 16:9 aspect ratio and 1080p resolution
    # frame_width = 720
    # frame_height = 480  # Initial frame height for 16:9 aspect ratio and 720p resolution

    # # Calculate the frame width based on the aspect ratio
    # frame_width = int((frame_height / 9) * 16)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Tidak dapat membaca frame")
            break
        
        last_frame =frame
        
        # Encode the frame to JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        ########### baca data serial pada arduino #############
        # baca_data_arduino()
      
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()
    cv2.destroyAllWindows()
    
#################### function untuk last frame #################
def last_detection():
    global saved_frame
    while True:
        if saved_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + saved_frame + b'\r\n')
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
#################### function read camera index by csv #####################
def readCameraIndex():
    df = pd.read_csv('cameraConfig.csv')
    idx_cam_1 = df[df['camera_nm'] == 1]['camera_idx'][0]
    id_camera = idx_cam_1
    return id_camera

#################### hitung banyaknya file yang ada di direktory #####################
def count_files(directory):
    try:
        # List semua item dalam direktori
        items = os.listdir(directory)
        # Hitung berapa banyak item yang merupakan file
        file_count = sum([1 for item in items if os.path.isfile(os.path.join(directory, item))])
        return file_count
    except FileNotFoundError:
        return "Direktori tidak ditemukan."

#################### END POINT #####################
#============= Show Live Video ==============#
@collectSample.route('/collect/show-video')
def show_video():
    id_camera = readCameraIndex()
    print(f"====================  {id_camera}  ====================")
    print(f'Settings show video with camera index {id_camera}')
    return Response(stream_video(id_camera), mimetype='multipart/x-mixed-replace; boundary=frame')

#============= Show last images ==============#
@collectSample.route('/collect/last_detections', methods=['GET'])
def home_show_last():
    return Response(last_detection(), mimetype='multipart/x-mixed-replace; boundary=frame')


#============= save sample ==============#
@collectSample.route('/collect/save-sample', methods=['GET'])
def save_sample():
    global saved_frame, last_frame
    namafile = request.args.get('name', default='sample')
    folder = request.args.get('dir', default=namafile)
    imgPath = hptb.save_image(last_frame, namafile, folder)
    saved_frame = last_frame
    ret, buffer = cv2.imencode('.jpg', last_frame)
    
    # Update saved frame to the latest frame
    saved_frame = buffer.tobytes()
    
    #hitung jumlah file didalam direktori
    filecount = count_files(imgPath)
    return jsonify({'message': 'Sample saved',
                    'img_path': imgPath,
                    'count_file' : filecount})

#============= test controller ==============#
@collectSample.route('/collect/tipu', methods=['GET'])
def tipu_index():
    # show_data()
    return f"tipu-tipu-display {hptb.resetInspectionFlag}, {hptb.inspectionFlag}"