import os
from PIL import Image
import io
from fastapi import UploadFile

def upload_test_photo(file: UploadFile, test_id: str, test_name: str) -> str:
    # Create directory if it doesn't exist
    upload_dir = f"uploads/lab_tests/{test_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Get file extension
    file_extension = os.path.splitext(file.filename)[1]
    # Clean test name for filename
    clean_test_name = "".join([c for c in test_name if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
    file_path = f"{upload_dir}/{clean_test_name}{file_extension}"
    
    # Read file content
    contents = file.file.read()
    image = Image.open(io.BytesIO(contents))
    
    # Convert to RGB if necessary (for JPEG compression)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    
    # Compress and save
    # We can adjust quality as needed, e.g., 70
    image.save(file_path, optimize=True, quality=70)
    
    return file_path

def delete_test_photo(photo_url: str):
    if photo_url and os.path.exists(photo_url):
        try:
            os.remove(photo_url)
            # Try to remove the directory if it's empty
            parent_dir = os.path.dirname(photo_url)
            if not os.listdir(parent_dir):
                os.rmdir(parent_dir)
        except Exception as e:
            print(f"Error deleting photo: {e}")
