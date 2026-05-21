import os
import shutil
from fastapi import UploadFile
from datetime import datetime


def clear_old_reports(booking_upload_dir: str) -> None:
    """
    Remove all old report files from the booking directory.
    
    Args:
        booking_upload_dir: Directory containing reports for a booking
    """
    try:
        if os.path.exists(booking_upload_dir):
            for filename in os.listdir(booking_upload_dir):
                file_path = os.path.join(booking_upload_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
    except Exception as e:
        raise Exception(f"Error clearing old reports: {str(e)}")


async def upload_report(
    booking_id: str,
    file: UploadFile,
    upload_dir: str = "uploads/lab_test_reports"
) -> str:
    """
    Upload PDF report file for a booking.
    Replaces old reports with new ones.
    
    Args:
        booking_id: Unique booking ID
        file: PDF UploadFile object
        upload_dir: Directory to store uploads
    
    Returns:
        file_url: Path to uploaded file
    """
    try:
        # Create booking-specific directory if it doesn't exist
        booking_upload_dir = os.path.join(upload_dir, booking_id)
        os.makedirs(booking_upload_dir, exist_ok=True)
        
        # Clear old reports
        clear_old_reports(booking_upload_dir)
        
        # Generate filename with report date
        report_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"report_{report_date}.pdf"
        file_path = os.path.join(booking_upload_dir, final_filename)
        
        # Save the PDF file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative URL path
        file_url = f"/uploads/lab_test_reports/{booking_id}/{final_filename}"
        return file_url
    
    except Exception as e:
        raise Exception(f"Error uploading report: {str(e)}")


async def upload_multiple_reports(
    booking_id: str,
    files: list,
    upload_dir: str = "uploads/lab_test_reports"
) -> list:
    """
    Upload multiple PDF report files for a booking.
    Replaces old reports with new ones.
    
    Args:
        booking_id: Unique booking ID
        files: List of PDF UploadFile objects
        upload_dir: Directory to store uploads
    
    Returns:
        file_urls: List of paths to uploaded files
    """
    file_urls = []
    booking_upload_dir = os.path.join(upload_dir, booking_id)
    
    try:
        # Create booking-specific directory if it doesn't exist
        os.makedirs(booking_upload_dir, exist_ok=True)
        
        # Clear old reports before uploading new ones
        clear_old_reports(booking_upload_dir)
        
        for file in files:
            try:
                # Generate filename with report date
                report_date = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_filename = f"report_{report_date}.pdf"
                file_path = os.path.join(booking_upload_dir, final_filename)
                
                # Save the PDF file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                file_url = f"/uploads/lab_test_reports/{booking_id}/{final_filename}"
                file_urls.append(file_url)
            except Exception as e:
                print(f"Error uploading file {file.filename}: {str(e)}")
        
        return file_urls
    
    except Exception as e:
        raise Exception(f"Error uploading multiple reports: {str(e)}")
