from ultralytics import YOLO

model_path = "/media/karim/20EEA70FEEA6DBF2/Python_projects/ai_oring/ai_oring_app/be-oring-ai/models/mix_augment_oringchain.pt"
model = YOLO(model_path)

print(model.names)