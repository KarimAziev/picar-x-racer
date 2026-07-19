from ultralytics import YOLO

# Load the OIV7 model
model = YOLO("yolov8n-oiv7.pt")

# Dynamically find the class index for 'Human face'
class_names = model.names  # This is a dictionary of {int: 'str'}
# face_index = [k for k, v in class_names.items() if v == "Human face"][0]

# print(f"The CLASS_INDEX for a human face is: {face_index}")
class_names
