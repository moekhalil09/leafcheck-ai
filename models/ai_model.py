# models/ai_model.py - MobileNetV2 with Attention version
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
import timm  # Add this import

from models.data_models import DiseaseCategory, DiseaseInfo, DiagnosisResult
from models.disease_database import get_disease_info
from config import CLASS_NAMES, IMAGE_SIZE, MODEL_PATH

logger = logging.getLogger(__name__)

# Bloc attention pour améliorer MobileNetV2
class SqueezeExcitation(nn.Module):
    def __init__(self, input_channels, reduction=16):
        super().__init__()
        self.squeeze = nn.AdaptiveAvgPool2d(1)
        self.excitation = nn.Sequential(
            nn.Linear(input_channels, input_channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(input_channels // reduction, input_channels, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.squeeze(x).view(b, c)
        y = self.excitation(y).view(b, c, 1, 1)
        return x * y

# MobileNetV2 avec attention
class AttentiveMobileNetV2(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.backbone = timm.create_model('mobilenetv2_100', pretrained=True, num_classes=0, global_pool='')
        self.attention = SqueezeExcitation(1280)
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Linear(1280, num_classes)

    def forward(self, x):
        x = self.backbone(x)
        x = self.attention(x)
        x = self.global_pool(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)

class LeafDiseaseModel:
    """Attentive MobileNetV2 wrapper for plant disease detection"""
    
    def __init__(self, model_path: Optional[Path] = None, threshold: float = 0.40):
        self.model_path = model_path or MODEL_PATH
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.threshold = threshold  # Confidence threshold for accepting predictions
        self.model = None
        self.transform = self._get_transforms()
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        self._load_model()
        logger.info(f"Attentive MobileNetV2 model loaded on {self.device}")
    
    def _get_transforms(self):
        """Image transformations for MobileNetV2"""
        return transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet stats
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def _load_model(self):
        """Load AttentiveMobileNetV2 model from .pth file"""
        try:
            # Create AttentiveMobileNetV2 architecture
            self.model = AttentiveMobileNetV2(num_classes=len(CLASS_NAMES))
            
            # Load state dict
            state_dict = torch.load(self.model_path, map_location=self.device)
            
            # Handle different state dict formats
            if isinstance(state_dict, nn.Module):
                self.model = state_dict
            elif 'model_state_dict' in state_dict:
                self.model.load_state_dict(state_dict['model_state_dict'])
            elif 'state_dict' in state_dict:
                self.model.load_state_dict(state_dict['state_dict'])
            else:
                # Try to load directly
                self.model.load_state_dict(state_dict)
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Attentive MobileNetV2 model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading Attentive MobileNetV2 model: {e}")
            raise RuntimeError(f"Cannot load model: {e}")
    
    def preprocess_image(self, image_input: Union[str, Path, Image.Image]) -> torch.Tensor:
        try:
            # Load image
            if isinstance(image_input, (str, Path)):
                image = Image.open(image_input).convert('RGB')
            elif isinstance(image_input, Image.Image):
                image = image_input.convert('RGB')
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")
            
            # Store original size
            original_size = image.size
            
            # Log original size
            logger.debug(f"Original image size: {original_size}")
            
            # Apply transformations
            image_tensor = self.transform(image)
            
            # Log transformed size
            logger.debug(f"Transformed tensor shape: {image_tensor.shape}")
            
            # Add batch dimension
            image_tensor = image_tensor.unsqueeze(0).to(self.device)
            
            return image_tensor
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
    
    def predict(self, image_input: Union[str, Path, Image.Image]) -> DiagnosisResult:
        """Make prediction on an image with confidence threshold"""
        start_time = time.time()
        
        try:
            # Store original image info
            if isinstance(image_input, (str, Path)):
                image_path = str(image_input)
                try:
                    image = Image.open(image_path)
                    image_size = image.size
                    image.close()
                except:
                    image_path = None
                    image_size = (0, 0)
            elif isinstance(image_input, Image.Image):
                image_path = None
                image_size = image_input.size
                image = image_input
            else:
                image_path = None
                image_size = (0, 0)
            
            # Preprocess image
            image_tensor = self.preprocess_image(image_input)
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
            
            inference_time = time.time() - start_time
            
            # Get top prediction
            confidence, pred_idx = torch.max(probabilities, dim=1)
            confidence = confidence.item()
            pred_idx = pred_idx.item()
            
            # Check confidence threshold
            if confidence < self.threshold:
                # REJECTED: Not a recognized Tomato Leaf
                rejected_disease = DiseaseInfo(
                    name="rejected",
                    display_name="Not a recognized Tomato Leaf",
                    category=DiseaseCategory.UNKNOWN,
                    description=f"Confidence too low: {confidence:.2%} < {self.threshold:.0%}"
                )
                
                diagnosis = DiagnosisResult(
                    disease=rejected_disease,
                    confidence=confidence,
                    inference_time=inference_time,
                    image_path=image_path,
                    image_size=image_size,
                    top_predictions=[],  # No top predictions for rejected
                    is_rejected=True  # Add flag to indicate rejection
                )
                
                logger.info(f"REJECTED: Not a recognized Tomato Leaf "
                          f"(Confidence: {confidence:.2%} < {self.threshold:.0%}) "
                          f"in {inference_time:.3f}s")
                
                return diagnosis
            
            # ACCEPTED: Get disease info
            class_name = CLASS_NAMES[pred_idx]
            disease_info = get_disease_info(class_name)
            
            # Get top 3 predictions for accepted cases
            top_k = min(3, len(CLASS_NAMES))
            top_probs, top_indices = torch.topk(probabilities, top_k)
            
            top_predictions = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                top_class_name = CLASS_NAMES[idx]
                top_disease_info = get_disease_info(top_class_name)
                
                top_predictions.append({
                    'disease': top_disease_info,
                    'confidence': prob.item(),
                    'class_index': idx.item()
                })
            
            # Create DiagnosisResult for accepted prediction
            diagnosis = DiagnosisResult(
                disease=disease_info,
                confidence=confidence,
                inference_time=inference_time,
                image_path=image_path,
                image_size=image_size,
                top_predictions=top_predictions,
                is_rejected=False
            )
            
            logger.info(f"ACCEPTED: {disease_info.display_name} "
                      f"({diagnosis.get_confidence_percent()}) "
                      f"in {inference_time:.3f}s | "
                      f"Original size: {image_size}")
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            error_disease = DiseaseInfo(
                name="error",
                display_name="Prediction Error",
                category=DiseaseCategory.UNKNOWN,
                description=f"Error during prediction: {str(e)[:100]}"
            )
            return DiagnosisResult(
                disease=error_disease,
                confidence=0.0,
                inference_time=0.0,
                image_path=image_path if 'image_path' in locals() else None,
                image_size=image_size if 'image_size' in locals() else None,
                is_rejected=True
            )
    
    def predict_batch(self, image_paths: List[Union[str, Path]]) -> List[DiagnosisResult]:
        """Make predictions on multiple images"""
        results = []
        for image_path in image_paths:
            try:
                result = self.predict(image_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error predicting {image_path}: {e}")
                error_disease = DiseaseInfo(
                    name="error",
                    display_name="Prediction Error",
                    category=DiseaseCategory.UNKNOWN,
                    description=f"Error during prediction: {str(e)[:100]}"
                )
                error_result = DiagnosisResult(
                    disease=error_disease,
                    confidence=0.0,
                    inference_time=0.0,
                    image_path=str(image_path),
                    is_rejected=True
                )
                results.append(error_result)
        
        return results
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        
        return {
            "architecture": "AttentiveMobileNetV2",
            "device": str(self.device),
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "num_classes": len(CLASS_NAMES),
            "image_size": IMAGE_SIZE,
            "model_path": str(self.model_path),
            "confidence_threshold": self.threshold
        }
    
    def set_threshold(self, threshold: float):
        """Update the confidence threshold"""
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
            logger.info(f"Confidence threshold updated to: {threshold:.0%}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")