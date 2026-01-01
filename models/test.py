# test_step3.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config import CLASS_NAMES
from models.data_models import DiagnosisResult, DiseaseCategory
from models.disease_database import get_disease_info

print("Testing Data Models")
print("=" * 50)

# Test 1: Check all diseases exist
print("1. Testing disease database...")
for disease_name in CLASS_NAMES:
    disease_info = get_disease_info(disease_name)
    print(f"   {disease_info.display_name:25} [{disease_info.category.value}]")

# Test 2: Create diagnosis result
print("\n2. Testing diagnosis result...")
test_disease = get_disease_info("Tomato_Early_blight")
diagnosis = DiagnosisResult(
    disease=test_disease,
    confidence=0.85,
    inference_time=0.25,
    image_path="test_image.jpg",
    image_size=(800, 600)
)

print(f"   Disease: {diagnosis.disease.display_name}")
print(f"   Category: {diagnosis.disease.category.value}")
print(f"   Confidence: {diagnosis.get_confidence_percent()}")
print(f"   Healthy: {diagnosis.is_healthy()}")
print(f"   Color: {diagnosis.disease.get_color_hex()}")

# Test 3: Convert to dict
print("\n3. Testing dictionary conversion...")
dict_result = diagnosis.to_dict()
print(f"   Keys: {list(dict_result.keys())}")

print("\n" + "=" * 50)
print("Step 3 Complete. Ready for Step 4: ML Model Wrapper.")