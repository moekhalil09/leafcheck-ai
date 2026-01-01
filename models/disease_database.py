# models/disease_database.py - UPDATED FOR 8 CLASSES
from models.data_models import DiseaseInfo, DiseaseCategory
from config import CLASS_NAMES  # Import from config

# Disease database - mapped to YOUR FRIEND'S 8 CLASSES
DISEASE_DATABASE = {
    # ⚠️ MUST MATCH EXACTLY THE NAMES IN CLASS_NAMES ⚠️
    
    "Tomato_Early_Blight": DiseaseInfo(
        name="Tomato_Early_Blight",
        display_name="Early Blight",
        category=DiseaseCategory.FUNGAL,
        description="Fungal disease causing target-like spots with concentric rings",
        symptoms=[
            "Dark spots with concentric rings",
            "Yellow halos around spots",
            "Lower leaves affected first"
        ],
        treatment=[
            "Remove infected leaves",
            "Apply fungicides (chlorothalonil)",
            "Improve air circulation"
        ],
        prevention=[
            "Crop rotation",
            "Proper spacing between plants",
            "Avoid overhead watering"
        ],
        severity="medium"
    ),
    
    "Tomato_Late_Blight": DiseaseInfo(
        name="Tomato_Late_Blight",
        display_name="Late Blight",
        category=DiseaseCategory.FUNGAL,
        description="Destructive fungal disease that can kill plants quickly",
        symptoms=[
            "Gray-green water-soaked spots",
            "White fungal growth on underside",
            "Rapid wilting and browning"
        ],
        treatment=[
            "Apply fungicides immediately",
            "Remove and destroy infected plants",
            "Isolate affected area"
        ],
        prevention=[
            "Use resistant varieties",
            "Avoid wet foliage",
            "Ensure good drainage"
        ],
        severity="high"
    ),
    
    "Tomato_Leaf_Mold": DiseaseInfo(
        name="Tomato_Leaf_Mold",
        display_name="Leaf Mold",
        category=DiseaseCategory.FUNGAL,
        description="Fungal disease common in humid greenhouse conditions",
        symptoms=[
            "Yellow patches on upper leaf surface",
            "Grayish-purple mold on underside",
            "Leaves curl and die"
        ],
        treatment=[
            "Apply fungicides",
            "Improve ventilation",
            "Reduce humidity"
        ],
        prevention=[
            "Increase air circulation",
            "Use resistant varieties",
            "Space plants properly"
        ],
        severity="medium"
    ),
    
    "Tomato_Septoria_leaf_spot": DiseaseInfo(
        name="Tomato_Septoria_leaf_spot",
        display_name="Septoria Leaf Spot",
        category=DiseaseCategory.FUNGAL,
        description="Fungal disease characterized by numerous small spots",
        symptoms=[
            "Many small circular spots (1-3mm)",
            "Spots have dark brown margins",
            "Yellowing of affected leaves"
        ],
        treatment=[
            "Remove infected leaves",
            "Apply copper-based fungicides",
            "Improve air flow"
        ],
        prevention=[
            "Clean garden debris",
            "Rotate crops",
            "Avoid working with wet plants"
        ],
        severity="medium"
    ),
    
    "Tomato_Bacterial_Spot": DiseaseInfo(  # Note: "Spot" not "spot"
        name="Tomato_Bacterial_Spot",
        display_name="Bacterial Spot",
        category=DiseaseCategory.BACTERIAL,
        description="Bacterial infection causing small, dark lesions",
        symptoms=[
            "Small, dark, water-soaked spots",
            "Yellow halos around spots",
            "Spots may coalesce"
        ],
        treatment=[
            "Apply copper bactericides",
            "Remove severely infected plants",
            "Avoid overhead irrigation"
        ],
        prevention=[
            "Use disease-free seeds",
            "Practice crop rotation",
            "Disinfect tools"
        ],
        severity="medium"
    ),
    
    "Tomato_mosaic_virus": DiseaseInfo(
        name="Tomato_mosaic_virus",
        display_name="Mosaic Virus",
        category=DiseaseCategory.VIRAL,
        description="Viral disease causing mottled leaf patterns",
        symptoms=[
            "Mottled light and dark green patterns",
            "Leaf distortion and curling",
            "Stunted plant growth"
        ],
        treatment=[
            "No cure - remove infected plants",
            "Control aphid vectors",
            "Sterilize tools"
        ],
        prevention=[
            "Use virus-free seeds",
            "Wash hands before handling",
            "Control insect vectors"
        ],
        severity="high"
    ),
    
    "Tomato_Yellow_Leaf_Curl_Virus": DiseaseInfo(
        name="Tomato_Yellow_Leaf_Curl_Virus",
        display_name="Yellow Leaf Curl Virus",
        category=DiseaseCategory.VIRAL,
        description="Viral disease transmitted by whiteflies",
        symptoms=[
            "Upward curling of leaf edges",
            "Yellowing between veins",
            "Reduced fruit size"
        ],
        treatment=[
            "Remove infected plants",
            "Control whitefly populations",
            "Use insecticidal soaps"
        ],
        prevention=[
            "Use resistant varieties",
            "Install insect netting",
            "Monitor for whiteflies"
        ],
        severity="critical"
    ),
    
    "Tomato_Healthy": DiseaseInfo(  # Note: Capital H
        name="Tomato_Healthy",
        display_name="Healthy Tomato",
        category=DiseaseCategory.HEALTHY,
        description="Plant shows no signs of disease or pests",
        symptoms=["Vibrant green color", "Normal leaf shape", "Good growth"],
        treatment=["Continue regular care", "Monitor regularly"],
        prevention=["Proper watering", "Balanced fertilization", "Regular inspection"],
        severity="none"
    ),
    
    # Special cases for system use
    "rejected": DiseaseInfo(
        name="rejected",
        display_name="Not Recognized",
        category=DiseaseCategory.UNKNOWN,
        description="Image doesn't appear to be a recognizable tomato leaf or confidence is too low",
        symptoms=["Low prediction confidence"],
        treatment=["Upload a clearer image", "Ensure it's a tomato leaf"],
        prevention=["Use clear, focused images"],
        severity="none"
    ),
    
    "error": DiseaseInfo(
        name="error",
        display_name="Prediction Error",
        category=DiseaseCategory.UNKNOWN,
        description="An error occurred during prediction",
        symptoms=["System error"],
        treatment=["Try again", "Check image format"],
        prevention=["Ensure valid image file"],
        severity="none"
    )
}

def get_disease_info(disease_name: str) -> DiseaseInfo:
    """Get disease information by name"""
    # Clean the name
    clean_name = disease_name.strip()
    
    # First, try exact match
    if clean_name in DISEASE_DATABASE:
        return DISEASE_DATABASE[clean_name]
    
    # Try case-insensitive match
    for key in DISEASE_DATABASE.keys():
        if clean_name.lower() == key.lower():
            return DISEASE_DATABASE[key]
    
    # Try partial match (for variations)
    for key in DISEASE_DATABASE.keys():
        if clean_name.lower() in key.lower() or key.lower() in clean_name.lower():
            return DISEASE_DATABASE[key]
    
    # If not found, check if it's one of our CLASS_NAMES but not in database
    if clean_name in CLASS_NAMES:
        # Create a basic entry for missing disease
        display_name = clean_name.replace("_", " ").replace("Tomato ", "")
        return DiseaseInfo(
            name=clean_name,
            display_name=display_name,
            category=DiseaseCategory.UNKNOWN,
            description=f"Information for {display_name} not available",
            severity="unknown"
        )
    
    # Default unknown
    display_name = clean_name.replace("_", " ").title()
    return DiseaseInfo(
        name=clean_name,
        display_name=display_name,
        category=DiseaseCategory.UNKNOWN,
        description="Unknown disease or condition",
        severity="unknown"
    )

def get_all_diseases():
    """Get all diseases in the database"""
    return DISEASE_DATABASE

def get_healthy_disease():
    """Get the healthy plant disease info"""
    return DISEASE_DATABASE.get("Tomato_Healthy", 
        DiseaseInfo(
            name="Tomato_Healthy",
            display_name="Healthy",
            category=DiseaseCategory.HEALTHY,
            description="Healthy plant"
        )
    )

def get_rejected_disease():
    """Get the rejected disease info"""
    return DISEASE_DATABASE.get("rejected",
        DiseaseInfo(
            name="rejected",
            display_name="Not Recognized",
            category=DiseaseCategory.UNKNOWN,
            description="Not a recognized tomato leaf"
        )
    )

def get_error_disease():
    """Get the error disease info"""
    return DISEASE_DATABASE.get("error",
        DiseaseInfo(
            name="error",
            display_name="Error",
            category=DiseaseCategory.UNKNOWN,
            description="Prediction error"
        )
    )