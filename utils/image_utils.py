# utils/image_utils.py - ENHANCED VERSION
from PyQt5.QtGui import QPixmap, QImage, QPainter, QBrush, QColor
from PyQt5.QtCore import Qt, QSize
from config import SUPPORTED_EXTENSIONS, IMAGE_SIZE
import os
from pathlib import Path
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def load_image_to_pixmap(image_path: str, max_size: Tuple[int, int] = (400, 400)) -> QPixmap:
    """Load image file and convert to QPixmap for display with better error handling"""
    try:
        # Check file existence
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            return create_placeholder_pixmap("File not found", max_size)
        
        # Load directly with QPixmap
        pixmap = QPixmap(image_path)
        
        if pixmap.isNull():
            # Try with PIL as fallback
            try:
                from PIL import Image, ImageQt
                pil_image = Image.open(image_path).convert('RGB')
                
                # Convert PIL Image to QImage
                qimage = ImageQt.ImageQt(pil_image)
                pixmap = QPixmap.fromImage(qimage)
                
                if pixmap.isNull():
                    logger.error(f"Failed to convert PIL image to QPixmap: {image_path}")
                    return create_placeholder_pixmap("Invalid image", max_size)
                    
            except ImportError:
                logger.error("PIL/Pillow not installed for image fallback")
                return create_placeholder_pixmap("PIL not installed", max_size)
            except Exception as e:
                logger.error(f"PIL fallback failed for {image_path}: {e}")
                return create_placeholder_pixmap("Invalid format", max_size)
        
        # Create a properly sized pixmap for display
        return scale_pixmap_for_display(pixmap, max_size)
        
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        return create_placeholder_pixmap("Load error", max_size)

def scale_pixmap_for_display(pixmap: QPixmap, max_size: Tuple[int, int]) -> QPixmap:
    """Scale pixmap for display while maintaining aspect ratio"""
    if pixmap.isNull():
        return pixmap
    
    # Calculate scaled size
    original_width = pixmap.width()
    original_height = pixmap.height()
    max_width, max_height = max_size
    
    # Calculate scaling factor
    width_ratio = max_width / original_width
    height_ratio = max_height / original_height
    scale_factor = min(width_ratio, height_ratio)
    
    # Don't upscale small images
    if scale_factor > 1 and original_width < max_width and original_height < max_height:
        return pixmap
    
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    
    # Scale with smooth transformation
    return pixmap.scaled(
        new_width, new_height,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

def create_placeholder_pixmap(text: str, size: Tuple[int, int] = (200, 200)) -> QPixmap:
    """Create a placeholder pixmap with text"""
    width, height = size
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(240, 240, 240))  # Light gray background
    
    painter = QPainter(pixmap)
    
    # Draw border
    painter.setPen(QColor(200, 200, 200))
    painter.drawRect(0, 0, width - 1, height - 1)
    
    # Draw text
    painter.setPen(QColor(150, 150, 150))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    
    painter.end()
    return pixmap

def is_valid_image(file_path: str) -> bool:
    """Check if file is a valid image with more thorough validation"""
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return False
    
    # Check file size (max 10MB)
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"File too large: {file_size} bytes")
            return False
        if file_size == 0:
            logger.warning("File is empty")
            return False
    except:
        logger.warning("Could not determine file size")
    
    # Check extension
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Unsupported extension: {ext}")
        return False
    
    # Try to load with QPixmap
    pixmap = QPixmap(file_path)
    if not pixmap.isNull():
        return True
    
    # Try PIL as fallback
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            img.verify()  # Verify it's a valid image
            img.load()    # Load image data
        return True
    except Exception as e:
        logger.warning(f"PIL validation failed for {file_path}: {e}")
        return False

def get_image_info(image_path: str) -> Dict:
    """Get comprehensive image information"""
    info = {
        'filename': Path(image_path).name,
        'path': str(image_path),
        'size_bytes': 0,
        'dimensions': (0, 0),
        'format': 'Unknown',
        'aspect_ratio': 0,
        'valid': False,
        'error': None
    }
    
    try:
        # Get file size
        info['size_bytes'] = os.path.getsize(image_path)
        info['size_human'] = format_file_size(info['size_bytes'])
        
        # Try QPixmap first
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            info['dimensions'] = (pixmap.width(), pixmap.height())
            info['format'] = Path(image_path).suffix.upper().replace('.', '')
            info['aspect_ratio'] = pixmap.width() / pixmap.height() if pixmap.height() > 0 else 0
            info['valid'] = True
            return info
        
        # Fallback to PIL
        from PIL import Image
        with Image.open(image_path) as img:
            info['dimensions'] = img.size
            info['format'] = img.format or 'Unknown'
            info['mode'] = img.mode
            info['aspect_ratio'] = img.width / img.height if img.height > 0 else 0
            info['valid'] = True
            
    except Exception as e:
        info['error'] = str(e)
        info['valid'] = False
    
    return info

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def create_image_thumbnail(image_path: str, thumbnail_size: Tuple[int, int] = (100, 100)) -> QPixmap:
    """Create a thumbnail for image previews"""
    pixmap = load_image_to_pixmap(image_path, thumbnail_size)
    if pixmap.isNull():
        return create_placeholder_pixmap("Thumb", thumbnail_size)
    return pixmap

def preprocess_for_model(image_path: str) -> Optional[QImage]:
    """Preprocess image for model input (basic version)"""
    try:
        # Load image
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            # Try PIL fallback
            try:
                from PIL import Image
                pil_image = Image.open(image_path).convert('RGB')
                pil_image = pil_image.resize(IMAGE_SIZE)
                qimage = QImage(pil_image.tobytes(), pil_image.width, pil_image.height, QImage.Format_RGB888)
                return qimage
            except:
                return None
        
        # Convert to QImage and resize
        image = pixmap.toImage()
        if image.isNull():
            return None
        
        # Convert to RGB if necessary
        if image.format() != QImage.Format_RGB888:
            image = image.convertToFormat(QImage.Format_RGB888)
        
        # Resize to model input size
        scaled_image = image.scaled(
            IMAGE_SIZE[0], IMAGE_SIZE[1],
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )
        
        return scaled_image
        
    except Exception as e:
        logger.error(f"Error preprocessing image {image_path}: {e}")
        return None

def get_supported_extensions_filter() -> str:
    """Get file filter string for QFileDialog"""
    extensions = []
    for ext in SUPPORTED_EXTENSIONS:
        ext_upper = ext.upper().replace('.', '')
        extensions.append(f"*.{ext_upper.lower()}")
    
    all_extensions = " ".join(extensions)
    return f"Images ({all_extensions})"

def check_image_requirements(image_path: str) -> Tuple[bool, str]:
    """Check if image meets requirements for analysis"""
    # Check basic validity
    if not is_valid_image(image_path):
        return False, "Invalid image file"
    
    # Get image info
    info = get_image_info(image_path)
    if not info['valid']:
        return False, f"Cannot read image: {info.get('error', 'Unknown error')}"
    
    # Check minimum dimensions (optional)
    width, height = info['dimensions']
    if width < 50 or height < 50:
        return False, f"Image too small ({width}x{height}). Minimum 50x50 pixels."
    
    # Check aspect ratio (optional)
    aspect_ratio = info['aspect_ratio']
    if aspect_ratio < 0.2 or aspect_ratio > 5:
        return False, "Image aspect ratio too extreme"
    
    return True, "Image meets requirements"

def batch_validate_images(image_paths: list) -> Dict:
    """Validate multiple images and return results"""
    results = {
        'valid': [],
        'invalid': [],
        'errors': []
    }
    
    for image_path in image_paths:
        try:
            if is_valid_image(image_path):
                results['valid'].append(image_path)
            else:
                results['invalid'].append(image_path)
        except Exception as e:
            results['errors'].append({
                'path': image_path,
                'error': str(e)
            })
    
    return results

# Additional utility for image manipulation
def apply_image_overlay(base_pixmap: QPixmap, overlay_text: str) -> QPixmap:
    """Apply text overlay to pixmap (for showing results on image)"""
    result = QPixmap(base_pixmap)
    painter = QPainter(result)
    
    # Semi-transparent background for text
    painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, result.width(), 40)
    
    # Text
    painter.setPen(Qt.white)
    painter.setFont(QPainter.font(painter).family(), 12)
    painter.drawText(10, 25, overlay_text)
    
    painter.end()
    return result

def save_pixmap_to_file(pixmap: QPixmap, file_path: str) -> bool:
    """Save QPixmap to file"""
    try:
        # Determine format from extension
        ext = Path(file_path).suffix.lower()
        format_map = {
            '.png': 'PNG',
            '.jpg': 'JPG',
            '.jpeg': 'JPG',
            '.bmp': 'BMP',
            '.webp': 'WEBP'
        }
        
        format = format_map.get(ext, 'PNG')
        return pixmap.save(file_path, format)
    except Exception as e:
        logger.error(f"Error saving pixmap to {file_path}: {e}")
        return False