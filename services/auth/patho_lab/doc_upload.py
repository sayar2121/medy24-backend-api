import os
from PIL import Image
import shutil
from fastapi import UploadFile

UPLOAD_DIR = "uploads/auth"

def save_and_compress_file(file: UploadFile, lab_id: str, field_name: str):
    # Create directory if not exists
    target_dir = os.path.join(UPLOAD_DIR, lab_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Get extension
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        # Fallback for some browsers/files
        ext = ".jpg"
        
    filename = f"{field_name}{ext}"
    file_path = os.path.join(target_dir, filename)
    
    # Check if it's an image for compression
    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
        try:
            img = Image.open(file.file)
            # Convert to RGB if necessary (e.g. for PNG to JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Save with compression
            img.save(file_path, optimize=True, quality=70)
        except Exception as e:
            # If compression fails, save as is
            print(f"Compression failed for {filename}: {e}")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
    else:
        # For PDF and other files, save as is
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    return file_path
