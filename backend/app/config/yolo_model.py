import torch
from torchvision import models, transforms

# torch.backends.quantized.engine = "qnnpack"

# net = models.quantization.mobilenet_v2(
#     weights=models.quantization.MobileNet_V2_QuantizedWeights.IMAGENET1K_QNNPACK_V1,
#     quantize=True,
# )
# net = torch.jit.script(net)


# net.eval()  # type: ignore
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# yolo_model = torch.hub.load("ultralytics/yolov5", "yolov5n", pretrained=True)
# preprocess = transforms.Compose(
#     [
#         transforms.Resize((224, 224)),
#         transforms.ToTensor(),
#         transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
#     ]
# )
