import os
from PIL import Image
from fastapi import UploadFile
import uuid

UPLOAD_DIR = "uploads/about_us"

def create_upload_dir():
    """Create uploads directory if it doesn't exist"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def compress_image(image: Image.Image, quality: int = 85) -> Image.Image:
    """Compress image while maintaining quality"""
    return image

def upload_about_us_photo(file: UploadFile, param_name: str) -> str:
    """
    Upload and compress photo for About Us section
    
    Args:
        file: UploadFile object
        param_name: Parameter name (company_photo, director_photo, etc.)
    
    Returns:
        str: File path/URL of the uploaded image
    """
    create_upload_dir()
    
    try:
        # Generate unique filename with parameter name
        file_extension = file.filename.split('.')[-1]
        filename = f"{param_name}_{uuid.uuid4().hex}.{file_extension}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Open, compress, and save image
        image = Image.open(file.file)
        
        # Compress image
        if image.mode in ('RGBA', 'LA', 'P'):
            # Convert RGBA/LA/P to RGB
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = rgb_image
        
        # Resize if too large (max width 2000px)
        max_width = 2000
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save compressed image
        image.save(filepath, quality=85, optimize=True)
        
        return filepath
    
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return None

def delete_about_us_photo(filepath: str) -> bool:
    """
    Delete a photo from uploads directory
    
    Args:
        filepath: Path to the file to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        print(f"Error deleting photo: {e}")
        return False
