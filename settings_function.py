from flask import Blueprint, Response, request, jsonify
from flask_cors import CORS
import cv2
import os
import pandas as pd
import datetime
import time
import numpy as np

settings = Blueprint('settings_routes', __name__)
CORS(settings)

latest_frame = None

id_camera = 0
zoom_level = 100
zoom_increment = 10
focus_level = 0
focus_increment = 5

def disable_autofocus_with_v4l2(device, focus_value):
    # Menonaktifkan autofokus
    os.system(f"sudo v4l2-ctl -d {device} -c focus_automatic_continuous=0")
    print("Autofokus dinonaktifkan")

    print("dah masuk fungsi")
    # new_focus = int(input("Set focus :"))
    # Mengatur fokus manual ke nilai tertentu, misalnya 1010
    os.system(f"sudo v4l2-ctl -d {device} -c focus_absolute={focus_value}")
    print(f"Fokus diatur ke {focus_value}")

def setting_zoom(device, zoom_level):
    os.system(f"v4l2-ctl -d {device} -c zoom_absolute={zoom_level}")
    print(f"Zoom diatur ke {zoom_level}")
  
def stream_video(device):
    global zoom_level, focus_level, latest_frame
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
    
    # # Set frame width and height for 16:9 aspect ratio and 1080p resolution
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
        latest_frame = frame
        
        # # Set frame width and height for 16:9 aspect ratio and 1080p resolution
        # frame_width = 1280
        # frame_height = 720  # Initial frame height for 16:9 aspect ratio and 720p resolution

        # # Calculate the frame width based on the aspect ratio
        # frame_width = int((frame_height / 9) * 16)
        # frame = cv2.resize(frame, (int(frame_width * (810 / frame_height)), 810))
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()
    cv2.destroyAllWindows()


def updateIndexMainCamera():
    global id_camera
    df = pd.read_csv('cameraConfig.csv')
    idx_cam_1 = df[df['camera_nm'] == 1]['camera_idx'][0]
    id_camera = idx_cam_1
    
updateIndexMainCamera()
    
################################### streaming image to client   #################################################
@settings.route('/settings-show-video', methods=['GET'])
def settings_show_video():
    print(f'Settings show video with camera index {id_camera}')
    return Response(stream_video(id_camera), mimetype='multipart/x-mixed-replace; boundary=frame')

################################### setting focus parameters   #################################################
@settings.route('/settings-focus', methods=['GET'])
def settings_focus():
    global focus_level
    focus = request.args.get('focus')   #membaca data input dari request
    focus_level = focus                 #menyalin nilai current input ke variabel global
    disable_autofocus_with_v4l2(id_camera, focus_value=focus)   #disabling auto focus and setting manual focus
    print("Focus is set to " + focus)
    return Response(focus, mimetype='multipart/')

################################### setting zoom  #################################################
@settings.route('/settings-zoom', methods=['GET'])
def zoom():
    global zoom_level
    zoom = request.args.get('zoom')   #membaca data input dari request
    zoom_level = zoom                 #menyalin nilai current input ke variabel global
    setting_zoom(id_camera, zoom_level=zoom_level)
    print("Zoom is set to " + zoom)
    return Response(zoom, mimetype='multipart/')

################################### switch camera by input   #################################################
@settings.route('/settings-camera-index', methods=['GET'])
def set_camera():
    global id_camera
    new_camera = request.args.get('cam_id')   #membaca data input dari request
    new_camera_value = int(new_camera)
        
    if new_camera_value >= 0:
        id_camera = new_camera_value
            
    print(f"Camera id is set to {id_camera}")
    return Response(str(id_camera))

################################### switch camera by index   #################################################
@settings.route('/settings/switch-camera-index', methods=['GET'])
def switch_camera():
    global id_camera
    direction = request.args.get('direction')   #membaca data input dari request
    switch_direction = int(direction)
        
    if switch_direction == 1:
        id_camera = id_camera + 1
        
    else:
        id_camera = id_camera - 1
            
    print(f"Camera id is set to {id_camera}")
    return Response(str(id_camera))

################################### Save images  #################################################
@settings.route('/settings-save-images', methods=['GET'])
def save_images():
    global latest_frame
    raw_name = request.args.get('name')
    corrected_name = raw_name.replace(' ', '_')

    # Get current date and time for saving the file name.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{corrected_name}_{timestamp}"
    
    # Buat Direktory download
    current_directory = os.path.dirname(os.path.abspath(__file__))
    downloads_directory = os.path.join(current_directory, 'Downloads')
    os.makedirs(downloads_directory, exist_ok=True)
    
    #simpan ke direktori download
    image_path = os.path.join(downloads_directory, f"{file_name}.png")  # Menambahkan timestamp pada nama file
    
    cv2.imwrite(image_path, latest_frame)
    print(f"Gambar disimpan di {image_path}")
    
    data = {
        'message': 'sucess save images',
        'filename': file_name,
    }
    # Mengembalikan respons JSON
    return jsonify(data)

##########################    reset camera params    ##############################################################################
@settings.route('/settings-reset', methods=['GET'])
def reset_settings():
    global zoom_level, focus_level, id_camera
    zoom_level = 100
    focus_level = 0
    disable_autofocus_with_v4l2(id_camera, focus_value=focus_level)
    setting_zoom(id_camera, zoom_level=zoom_level)
    
    new_params = {'zoom level' : zoom_level, 'focus level' : focus_level}
    data = {
        'message': 'success masuk reset settings',
        'new_params': new_params,
    }
    
    # Mengembalikan respons JSON
    return jsonify(data)    

##########################    SAVE DATA PARAMETER BY INDEX CAMERA    ##############################################################################
@settings.route('/settings-save', methods=['GET'])
def save_settings():
    global zoom_level, focus_level, id_camera
    print('saving parameters')
    df = pd.read_csv('camera_parameters.csv')
# Convert data to a pandas DataFrame
    df = pd.DataFrame(df)

    # New data to update or add
    new_data = {
        'id_camera': id_camera,
        'focus_value': focus_level,
        'zoom_level': zoom_level,
    }

    new_df = pd.DataFrame([new_data])

    # Check if id_camera exists
    id_camera_exists = df['id_camera'] == new_data['id_camera']

    if id_camera_exists.any():
        # Update data if id_camera is found
        df.loc[df['id_camera'] == new_data['id_camera'], ['focus_value', 'zoom_level']] = new_data['focus_value'], new_data['zoom_level']
        print('Data diperbarui!')  # More descriptive message
    else:
        # Add new data if id_camera is not found
        df = pd.concat([df, new_df], ignore_index=True)
        print('Data baru ditambahkan!')  # More descriptive message

    df.to_csv('camera_parameters.csv', index=False)
    # Print the updated DataFrame
    print(df)
    data = {
        'message': 'success masuk save images',
        'new data': new_data
    }
    # print('level zoom:', zoom_level ,'focus_level:', focus_level, 'id_camera :', id_camera)
    # Mengembalikan respons JSON
    print('parameters saved')
    return jsonify(data)  


#################################   send data parameter to client   #################################################################
@settings.route('/settings-get', methods=['GET'])
def get_settings():
    global zoom_level, focus_level, id_camera
    df = pd.read_csv('camera_parameters.csv')
    camera_parameters = df.to_dict(orient='records')
    print(camera_parameters) 
    # Mengembalikan respons JSON
    return camera_parameters

@settings.route('/settings-get-camera-cfg', methods=['GET'])
def get_settings_cfg():
    df = pd.read_csv('cameraConfig.csv')
    camera_cfg = df.to_dict(orient='records')
    print(camera_cfg) 
    # Mengembalikan respons JSON
    return camera_cfg

@settings.route('/settings-update-camera-cfg', methods=['GET'])
def update_config():
    idx_cam_1 = request.args.get('camera_idx', default=0, type=int)
    
    data = [
    {"camera_nm": 1, "camera_idx": idx_cam_1},
    ]
    
    print(data)
    df = pd.DataFrame(data)
    
    df.to_csv('cameraConfig.csv', index=False)
     
    # Mengembalikan respons JSON
    return data

@settings.route('/tipu', methods=['GET'])
def tipu_index():
    return "tipu-tipu-index"
