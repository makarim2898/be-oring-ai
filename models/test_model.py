import cv2

from ultralytics import YOLO

# Load the YOLOv8 model
model = YOLO("/home/kaizen-ai/Desktop/thrust_bearing_app/python-backend/models/model1yolov10n.pt")

# Open the video file
cap = cv2.VideoCapture(0)

frame_width = 480
frame_height = 240

frame_width = int((frame_height / 9) * 16)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

# Loop through the video frames
while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()

    if success:
        # Run YOLOv8 inference on the frame
        results = model(frame, conf=0.6, max_det=2)

        # Visualize the results on the frame
        annotated_frame = results[0].plot()

        # Display the annotated frame
        cv2.imshow("YOLOv8 Inference", annotated_frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        # Break the loop if the end of the video is reached
        break

# Release the video capture object and close the display window
cap.release()
cv2.destroyAllWindows()