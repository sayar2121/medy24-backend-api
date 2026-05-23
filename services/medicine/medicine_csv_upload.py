import os
import shutil
from fastapi import UploadFile
from datetime import datetime


async def upload_medicine_csv(
    file: UploadFile,
    upload_dir: str = "uploads/core_medicines"
) -> str:
    """
    Upload CSV file containing medicine data.
    
    Args:
        file: CSV UploadFile object
        upload_dir: Directory to store uploads
    
    Returns:
        file_path: Path to uploaded CSV file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"medicines_{timestamp}{file_extension}"
        
        file_path = os.path.join(upload_dir, new_filename)
        
        # Save the CSV file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    
    except Exception as e:
        raise Exception(f"Error uploading CSV file: {str(e)}")
