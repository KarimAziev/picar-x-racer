import gc

import psutil
import torch
from app.config.paths import YOLO_MODEL_8_PATH
from ultralytics import YOLO


def print_memory_usage(description):
    # System RAM memory
    memory = psutil.virtual_memory()
    print(f"{description}:")
    print(f"System RAM - Total: {memory.total / (1024**3):.2f} GB")
    print(f"System RAM - Used: {memory.used / (1024**3):.2f} GB")
    print(f"System RAM - Available: {memory.available / (1024**3):.2f} GB")
    print(f"System RAM - Usage Percentage: {memory.percent}%")

    # GPU memory
    if torch.cuda.is_available():
        torch.cuda.synchronize()  # Wait for all kernels in all streams on a CUDA device to complete
        gpu_memory = torch.cuda.memory_stats(
            device=0
        )  # Get memory stats for the CUDA device
        print(
            f"GPU - Allocated: {gpu_memory['allocated_bytes.all.current'] / (1024**3):.2f} GB"
        )
        print(
            f"GPU - Cached: {gpu_memory['reserved_bytes.all.current'] / (1024**3):.2f} GB"
        )
    print()


class ModelManager:
    def __enter__(self):
        # "yolov8n.pt"
        self.model = YOLO(YOLO_MODEL_8_PATH)
        return self.model

    def __exit__(self, exc_type, exc_value, traceback):
        del self.model
        torch.cuda.synchronize()  # Wait for all CUDA operations to complete
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.synchronize()  # Final synchronization after cleanup
