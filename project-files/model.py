import io
import numpy as np
from PIL import Image
from ultralytics import YOLO
import concurrent.futures
import torch
import gc
from functools import lru_cache
import time
from typing import List, Tuple, Dict, Any, Optional
import threading

torch.backends.cudnn.benchmark = True
torch.set_grad_enabled(False)
torch.backends.cudnn.deterministic = False
torch.backends.cudnn.enabled = True

model_lock = threading.Lock()
models = []

class ModelManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with model_lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with model_lock:
                if not self._initialized:
                    self.weights = [
                        "",
                        "",
                    ]
                    self.models = self._initialize_models()
                    
                    self._initialized = True
    
    def _initialize_models(self) -> List[Tuple[str, YOLO]]:
        initialized_models = []
        for weight in self.weights:
            model = YOLO(weight)
            model.model.eval()
            if torch.cuda.is_available():
                model.model.half()
                model.model.cuda()
            initialized_models.append((weight, model))
        return initialized_models
    
    def _optimize_models(self):
        for _, model in self.models:
            if torch.cuda.is_available():
                torch.jit.trace(model.model, torch.randn(1, 3, 640, 640).cuda().half())
    
    @property
    def get_models(self) -> List[Tuple[str, YOLO]]:
        return self.models

@lru_cache(maxsize=32)
def preprocess_image(image_bytes: bytes, max_size: int = 640) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(image_bytes)).convert("RGB") as img:
            
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.LANCZOS)
            
            np_image = np.asarray(img, dtype=np.uint8)
            return np_image
    except Exception as e:
        print(f"Image preprocessing error: {str(e)}")
        raise

def run_inference(model_tuple: Tuple[str, YOLO], np_image: np.ndarray) -> Optional[Dict[str, Any]]:
    try:
        model_name, mdl = model_tuple
        start = time.perf_counter()
        
        with torch.cuda.amp.autocast() if torch.cuda.is_available() else nullcontext():
            
            results = mdl(np_image, verbose=False, conf=0.6)
        
        inference_time = time.perf_counter() - start

        
        print(f"Inference results for {model_name}: {results}")
        if results and len(results) > 0:
            print(f"Boxes data available: {hasattr(results[0], 'boxes') and results[0].boxes is not None and hasattr(results[0].boxes, 'conf') and results[0].boxes.conf.numel() > 0}")

        
        prediction_results = results[0]

        class_counts = {}
        sum_conf = 0.0
        num_boxes = 0

        detected_objects = None
        if hasattr(prediction_results, 'boxes') and prediction_results.boxes is not None:
            
            detected_objects = prediction_results.boxes
        elif hasattr(prediction_results, 'obb') and prediction_results.obb is not None and hasattr(prediction_results.obb, 'data'):
            
            detected_objects = prediction_results.obb.data
        elif hasattr(prediction_results, 'data') and prediction_results.data is not None:
             
             detected_objects = prediction_results.data
        

        if detected_objects is not None and len(detected_objects) > 0:
            
            confident_detections = detected_objects[detected_objects[:, 4] >= 0.6]

            if len(confident_detections) > 0:
                confs = confident_detections[:, 4].cpu().numpy()
                classes = confident_detections[:, 5].cpu().numpy()

                sum_conf = float(np.sum(confs))
                num_boxes = len(confident_detections)

                
                if len(classes) > 0:
                    unique_classes, counts = np.unique(classes, return_counts=True)
                    for cls, count in zip(unique_classes, counts):
                        
                        if int(cls) in prediction_results.names:
                            cls_name = prediction_results.names[int(cls)]
                            class_counts[cls_name] = int(count)
                        else:
                             print(f"Warning: Unknown class index {int(cls)} detected.")

        
        weight_conf = 1.0
        weight_unique = 1.5
        
        score = weight_conf * (sum_conf / num_boxes if num_boxes > 0 else 0.0) + weight_unique * len(class_counts)

        return {
            "result": prediction_results,
            "score": score,
            "inference_time": inference_time,
            "total_detections": num_boxes,
            "model_name": model_name,
            "class_counts": class_counts,
            "confidence_score": sum_conf / num_boxes if num_boxes > 0 else 0.0
        }

    except Exception as e:
        print(f"Inference error for model {model_name}: {str(e)}")
        
        import traceback
        traceback.print_exc()
        return None
    finally:
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def predict_image(image_bytes: bytes) -> Dict[str, Any]:
    try:
        
        model_manager = ModelManager()
        
        
        np_image = preprocess_image(image_bytes)
        
        best_data = None
        best_score = float('-inf')
        
        
        max_workers = min(len(model_manager.get_models), 
                         (torch.cuda.device_count() if torch.cuda.is_available() else 1) * 2)
        
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_model = {
                executor.submit(run_inference, model_tuple, np_image): model_tuple[0]
                for model_tuple in model_manager.get_models
            }
            
            for future in concurrent.futures.as_completed(future_to_model):
                data = future.result()
                if data is not None and data["score"] > best_score:
                    best_score = data["score"]
                    best_data = data

        if best_data is None:
            raise ValueError("No valid prediction results")

        
        best_result = best_data["result"]
        annotated_image = best_result.plot(labels=False, conf=False)
        
        
        with io.BytesIO() as buf:
            Image.fromarray(annotated_image).save(
                buf, 
                format="PNG", 
                optimize=True, 
                quality=95,
                compress_level=6
            )
            image_bytes = buf.getvalue()

        return {
            "processed_image": image_bytes,
            "model_name": best_data["model_name"],
            "execution_time": best_data["inference_time"],
            "class_counts": best_data["class_counts"],
            "confidence_score": best_data["confidence_score"],
            "total_detections": best_data["total_detections"]
        }

    except Exception as e:
        print(f"Prediction error: {str(e)}")
        raise
    finally:
        gc.collect()

class nullcontext:
    def __enter__(self): return None
    def __exit__(self, *args): return None

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"Memory Usage: {torch.cuda.memory_allocated(0)/1e9:.2f}GB")

def batch_predict_images(image_bytes_list: List[bytes], batch_size: int = 4):
    results = []
    for i in range(0, len(image_bytes_list), batch_size):
        batch = image_bytes_list[i:i + batch_size]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            batch_results = list(executor.map(predict_image, batch))
        results.extend(batch_results)
    return results
