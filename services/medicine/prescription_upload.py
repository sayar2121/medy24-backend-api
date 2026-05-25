import os
from PIL import Image
import shutil
from fastapi import UploadFile
from io import BytesIO

UPLOAD_DIR = "uploads/prescriptions"


def save_and_compress_prescription(file: UploadFile, order_id: str) -> str:
    """
    Upload and compress/save prescription file (image or PDF) for an order.
    
    Args:
        file: UploadFile object (image or PDF)
        order_id: Order ID for organizing uploads
    
    Returns:
        str: File path of the uploaded prescription
    """
    # Create directory if not exists
    target_dir = os.path.join(UPLOAD_DIR, order_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Get extension
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = ".jpg"
        
    filename = f"prescription{ext}"
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


def save_and_compress_prescription_bytes(file_data: bytes, filename: str, order_id: str) -> str:
    """
    Save and compress/store prescription file from base64 or bytes data for an order.
    Used for WebSocket uploads where we receive base64-encoded files.
    
    Args:
        file_data: Raw bytes of the file
        filename: Original filename or suggested filename with extension
        order_id: Order ID for organizing uploads
    
    Returns:
        str: File path of the saved prescription
    """
    # Create directory if not exists
    target_dir = os.path.join(UPLOAD_DIR, order_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Get extension
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        ext = ".jpg"
        
    filename = f"prescription{ext}"
    file_path = os.path.join(target_dir, filename)
    
    # Check if it's an image for compression
    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
        try:
            img = Image.open(BytesIO(file_data))
            # Convert to RGB if necessary (e.g. for PNG to JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Save with compression
            img.save(file_path, optimize=True, quality=70)
            print(f"✅ Image compressed and saved: {file_path}")
        except Exception as e:
            # If compression fails, save as is
            print(f"⚠️ Compression failed for {filename}, saving as-is: {e}")
            with open(file_path, "wb") as buffer:
                buffer.write(file_data)
    else:
        # For PDF and other files, save as is
        with open(file_path, "wb") as buffer:
            buffer.write(file_data)
        print(f"✅ File saved: {file_path}")
    
    return file_path


def delete_prescription(file_path: str) -> bool:
    """
    Delete a prescription file and its directory if empty.
    
    Args:
        file_path: Path to the prescription file
    
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Prescription file deleted: {file_path}")
            
            # Try to delete the order's prescription directory if empty
            prescription_dir = os.path.dirname(file_path)
            if os.path.exists(prescription_dir) and not os.listdir(prescription_dir):
                os.rmdir(prescription_dir)
                print(f"🗑️ Prescription directory deleted: {prescription_dir}")
            
            return True
    except Exception as e:
        print(f"⚠️ Failed to delete prescription file: {e}")
        return False
            
    return file_path


def delete_prescription(file_path: str) -> bool:
    """
    Delete a prescription file from uploads directory.
    
    Args:
        file_path: Path to the prescription file to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            # Try to remove the directory if it's empty
            parent_dir = os.path.dirname(file_path)
            if not os.listdir(parent_dir):
                os.rmdir(parent_dir)
        except Exception as e:
            print(f"Error deleting prescription file: {e}")
            return False
    return True
