# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"

# Create directories
for directory in [MODEL_DIR, ASSETS_DIR, DATA_DIR]:
    directory.mkdir(exist_ok=True)

# Model file - UPDATE WITH YOUR NEW MODEL FILENAME
MODEL_PATH = MODEL_DIR / "MobileNetV2_Attentive.pth"  # Changed filename

# Disease classes - 8 CLASSES (updated)
CLASS_NAMES = [
    "Tomato_Early_Blight",
    "Tomato_Late_Blight", 
    "Tomato_Leaf_Mold",
    "Tomato_Septoria_leaf_spot",
    "Tomato_Bacterial_Spot",
    "Tomato_mosaic_virus",
    "Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato_Healthy"
]

# Application settings
APP_NAME = "LeafCheckAI"
APP_VERSION = "1.1.0"  # Updated version

# Image settings
IMAGE_SIZE = (224, 224)  # Standard size for MobileNetV2
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png']

# Confidence threshold (from your friend's code)
DEFAULT_CONFIDENCE_THRESHOLD = 0.40

# Database settings
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "leafcheckai_db"
SCANS_COLLECTION = "scans"
PLANTS_COLLECTION = "plants"
USERS_COLLECTION = "users"

# Create .env file if it doesn't exist
env_file = BASE_DIR / ".env"
if not env_file.exists():
    with open(env_file, 'w') as f:
        f.write(f"MONGODB_URI={MONGODB_URI}\n")

# Debug
DEBUG = True