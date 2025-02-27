from ultralytics import YOLO

model_path = "models/rotate_varian_yolo11n.pt"
model = YOLO(model_path)

print(model.names)