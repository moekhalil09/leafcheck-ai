# models/data_models.py - FINAL VERSION WITH REJECTION SUPPORT
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from enum import Enum

class DiseaseCategory(Enum):
    BACTERIAL = "Bacterial"
    FUNGAL = "Fungal"
    VIRAL = "Viral"
    PEST = "Pest"
    HEALTHY = "Healthy"
    UNKNOWN = "Unknown"

@dataclass
class DiseaseInfo:
    """Information about a specific disease"""
    name: str  # Must match CLASS_NAMES in config
    display_name: str
    category: DiseaseCategory
    description: str = ""
    symptoms: List[str] = field(default_factory=list)
    treatment: List[str] = field(default_factory=list)
    prevention: List[str] = field(default_factory=list)
    severity: str = "low"  # low, medium, high, critical
    
    def get_color_hex(self) -> str:
        """Get color code based on severity/category"""
        if self.category == DiseaseCategory.HEALTHY:
            return "#4CAF50"  # Green
        elif self.category == DiseaseCategory.UNKNOWN:
            return "#9E9E9E"  # Gray for unknown/rejected
        elif self.severity == "critical":
            return "#F44336"  # Red
        elif self.severity == "high":
            return "#FF9800"  # Orange
        elif self.severity == "medium":
            return "#FFC107"  # Yellow
        else:
            return "#8BC34A"  # Light green

@dataclass
class DiagnosisResult:
    """Result from ML model prediction"""
    disease: DiseaseInfo
    confidence: float  # 0.0 to 1.0
    inference_time: float  # seconds
    timestamp: datetime = field(default_factory=datetime.now)
    image_path: Optional[str] = None
    image_size: Optional[Tuple[int, int]] = None  # (width, height)
    top_predictions: List[Dict] = field(default_factory=list)  # Top 3 predictions
    is_rejected: bool = False  # NEW: Whether prediction was rejected due to low confidence
    
    def is_healthy(self) -> bool:
        """Check if prediction is healthy"""
        return self.disease.category == DiseaseCategory.HEALTHY
    
    def get_confidence_percent(self) -> str:
        """Format confidence as percentage"""
        return f"{self.confidence * 100:.1f}%"
    
    def should_alert(self) -> bool:
        """Check if this diagnosis requires alert"""
        if self.is_rejected:
            return False  # Rejected predictions don't need alerts
        return self.disease.category in [DiseaseCategory.BACTERIAL, DiseaseCategory.FUNGAL, DiseaseCategory.VIRAL]
    
    def get_status(self) -> str:
        """Get human-readable status"""
        if self.is_rejected:
            return "Rejected (Low Confidence)"
        elif self.is_healthy():
            return "Healthy"
        else:
            return "Disease Detected"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "disease_name": self.disease.name,
            "display_name": self.disease.display_name,
            "confidence": self.confidence,
            "category": self.disease.category.value,
            "inference_time": self.inference_time,
            "timestamp": self.timestamp.isoformat(),
            "image_path": self.image_path,
            "severity": self.disease.severity,
            "is_rejected": self.is_rejected,
            "status": self.get_status(),
            "color": self.disease.get_color_hex()
        }
    
    def to_db_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "image_path": self.image_path or "",
            "image_size": self.image_size or (0, 0),
            "disease_name": self.disease.name,
            "display_name": self.disease.display_name,
            "category": self.disease.category.value,
            "confidence": float(self.confidence),
            "inference_time": float(self.inference_time),
            "timestamp": self.timestamp,
            "severity": self.disease.severity,
            "description": self.disease.description,
            "symptoms": self.disease.symptoms[:3],
            "treatment": self.disease.treatment[:3],
            "is_rejected": self.is_rejected,
            "top_predictions": [
                {
                    "disease_name": pred.get("disease", DiseaseInfo(name="Unknown", display_name="Unknown", category=DiseaseCategory.UNKNOWN)).name,
                    "confidence": float(pred.get("confidence", 0))
                }
                for pred in self.top_predictions[:3]
            ]
        }
    
    @classmethod
    def from_db_dict(cls, data: Dict) -> 'DiagnosisResult':
        """Create DiagnosisResult from database dictionary"""
        from models.disease_database import get_disease_info
        
        disease_info = get_disease_info(data["disease_name"])
        
        # Reconstruct top predictions
        top_predictions = []
        if "top_predictions" in data:
            for pred in data["top_predictions"]:
                pred_disease = get_disease_info(pred["disease_name"])
                top_predictions.append({
                    "disease": pred_disease,
                    "confidence": pred["confidence"]
                })
        
        # Handle timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return cls(
            disease=disease_info,
            confidence=data["confidence"],
            inference_time=data["inference_time"],
            timestamp=timestamp or datetime.now(),
            image_path=data.get("image_path"),
            image_size=data.get("image_size"),
            top_predictions=top_predictions,
            is_rejected=data.get("is_rejected", False)
        )

@dataclass
class ScanRecord:
    """Complete record of a scan"""
    id: Optional[str] = None
    plant_type: str = "tomato"
    image_path: str = ""
    diagnosis: Optional[DiagnosisResult] = None
    user_notes: str = ""
    location: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB"""
        data = {
            "plant_type": self.plant_type,
            "image_path": self.image_path,
            "user_notes": self.user_notes,
            "location": self.location,
            "created_at": self.created_at
        }
        
        if self.diagnosis:
            data["diagnosis"] = self.diagnosis.to_db_dict()
        
        if self.id:
            data["_id"] = self.id
            
        return data
    
    @classmethod
    def from_db_dict(cls, data: Dict) -> 'ScanRecord':
        """Create ScanRecord from database dictionary"""
        diagnosis = None
        if "diagnosis" in data:
            diagnosis = DiagnosisResult.from_db_dict(data["diagnosis"])
        
        return cls(
            id=str(data.get("_id")),
            plant_type=data.get("plant_type", "tomato"),
            image_path=data.get("image_path", ""),
            diagnosis=diagnosis,
            user_notes=data.get("user_notes", ""),
            location=data.get("location"),
            created_at=data.get("created_at", datetime.now())
        )