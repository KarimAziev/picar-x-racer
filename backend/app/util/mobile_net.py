
import numpy as np
import torch
from torchvision import models, transforms
from app.config.mobile_net_labels import labels
from app.config.yolo_model import device
from app.config.font import font
from app.util.logger import Logger
from PIL import Image, ImageDraw

logger = Logger(__name__)

torch.backends.quantized.engine = 'qnnpack'

net = models.quantization.mobilenet_v2(weights=models.quantization.MobileNet_V2_QuantizedWeights.IMAGENET1K_QNNPACK_V1, quantize=True)
net = torch.jit.script(net)

net.eval() # type: ignore

# Defining YOLO auxiliary
yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)

# Define the preprocess transformation
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def detect_objects_with_mobilenet(frame: np.ndarray) -> np.ndarray:
    """
    Detect objects in the frame using the pre-trained and quantized MobileNetV2 model.

    Args:
        frame (np.ndarray): Input frame for detection.

    Returns:
        np.ndarray: Frame with detected objects' labels.
    """
    border_color = (191, 255, 0)

    # Convert BGR to RGB as required by the model
    image = frame[:, :, [2, 1, 0]]

    # Convert to PIL image (required for transforms.Resize)
    pil_image = Image.fromarray(image)

    # Preprocess the image
    input_tensor = preprocess(pil_image)
    input_batch = input_tensor.unsqueeze(0).to(device)
    confidence_threshold = 0.4

    # Perform inference
    with torch.no_grad():
        output = net(input_batch) # type: ignore

    # Process the output from MobileNetV2
    try:
        # Softmax to get probabilities
        probabilities = output[0].softmax(dim=0)

        # Get top 5 predictions
        top5_prob, top5_idx = torch.topk(probabilities, 5)

        # Convert OpenCV image to PIL and prepare for drawing
        pil_frame = Image.fromarray(frame)
        draw = ImageDraw.Draw(pil_frame)



        for i, (idx, prob) in enumerate(zip(top5_idx, top5_prob)):
            if prob.item() > confidence_threshold:  # Reduced confidence threshold for debugging
                label = f"{labels[idx]}: {prob.item()*100:.2f}%"
                draw.text((10, 30 + 40*i), label, font=font, fill=border_color)

        yolo_results = yolo_model(frame)
        bbox_dataframe = yolo_results.pandas().xyxy[0]

        for _, row in bbox_dataframe.iterrows():
            x1, y1, x2, y2 = row['xmin'], row['ymin'], row['xmax'], row['ymax']
            confidence = row['confidence']
            class_pred = row['class']
            class_label = yolo_model.names[int(class_pred)]

            if confidence > confidence_threshold:
                draw.rectangle(((x1, y1), (x2, y2)), outline=border_color, width=2)
                draw.text((int(x1), int(y1)-10), f'{class_label}: {confidence:.2f}', font=font, fill=border_color)

        # Convert PIL image back to OpenCV format
        frame = np.array(pil_frame)

    except Exception as e:
        logger.error(f"Error in detect_objects_with_mobilenet: {e}")

    return frame
