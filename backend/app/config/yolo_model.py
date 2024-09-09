import torch


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)