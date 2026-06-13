import csv
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from models.medicine.core_medicine_models import CoreMedicine
from services.medicine.medicine_id_generator import generate_medicine_id


def calculate_final_selling_price(mrp: float, discount_percent: float = None) -> float:
    """
    Calculate final selling price based on MRP.
    Individual discounts have been removed globally. final_selling_price = mrp.
    """
    return mrp


def parse_precautions(precautions_str: str) -> list:
    """
    Parse precautions from CSV. Can be a JSON string or comma-separated values.
    """
    if not precautions_str or precautions_str.strip() == "":
        return []
    
    try:
        # Try to parse as JSON
        return json.loads(precautions_str)
    except (json.JSONDecodeError, ValueError):
        # If not JSON, split by comma
        return [p.strip() for p in precautions_str.split(",") if p.strip()]


def validate_medicine_row(row: Dict[str, str], row_num: int) -> Tuple[bool, str]:
    """
    Validate a single medicine row from CSV.
    Returns (is_valid, error_message)
    """
    required_fields = ["medicine_name", "medicine_category", "medicine_quantity", "mrp"]
    
    for field in required_fields:
        if field not in row or row[field].strip() == "":
            return False, f"Row {row_num}: Missing required field '{field}'"
    
    # Validate MRP is a valid float
    try:
        float(row["mrp"])
    except ValueError:
        return False, f"Row {row_num}: MRP must be a valid number"
    
    # Validate discount percent if provided
    if "discount_percent" in row and row["discount_percent"].strip() != "":
        try:
            float(row["discount_percent"])
        except ValueError:
            return False, f"Row {row_num}: discount_percent must be a valid number"
    
    return True, ""


def extract_medicines_from_csv(
    file_path: str,
    db: Session,
    batch_size: int = 500
) -> Dict[str, Any]:
    """
    Extract medicine data from CSV file and store in database using batch insertion.
    
    Expected CSV columns:
    - medicine_name (required)
    - medicine_category (required)
    - medicine_quantity (required)
    - mrp (required)
    - discount_percent (optional)
    - medicine_description (optional)
    - medicine_composition (optional)
    - precautions (optional - can be JSON array or comma-separated)
    - prescription_required (optional - "true" or "false", default "false")
    
    Args:
        file_path: Path to CSV file
        db: SQLAlchemy session
        batch_size: Number of records to insert per batch (default: 500)
    
    Returns:
        Dictionary with results containing:
        - total_rows: Total rows processed
        - successful: Number of medicines successfully added
        - failed: Number of failures
        - errors: List of error messages
        - created_medicines: List of created medicine IDs
    """
    results = {
        "total_rows": 0,
        "successful": 0,
        "failed": 0,
        "errors": [],
        "created_medicines": []
    }
    
    try:
        medicines_batch = []
        existing_medicines = set()
        
        # Get all existing medicines to avoid duplicates
        existing_records = db.query(CoreMedicine.medicine_name, CoreMedicine.medicine_category).all()
        for record in existing_records:
            existing_medicines.add((record[0], record[1]))
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames is None:
                results["errors"].append("CSV file is empty or invalid")
                return results
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
                results["total_rows"] += 1
                
                # Validate row
                is_valid, error_msg = validate_medicine_row(row, row_num)
                if not is_valid:
                    results["failed"] += 1
                    results["errors"].append(error_msg)
                    continue
                
                try:
                    medicine_name = row["medicine_name"]
                    medicine_category = row["medicine_category"]
                    
                    # Check if medicine already exists
                    if (medicine_name, medicine_category) in existing_medicines:
                        results["failed"] += 1
                        results["errors"].append(
                            f"Row {row_num}: Medicine '{medicine_name}' in category "
                            f"'{medicine_category}' already exists"
                        )
                        continue
                    
                    # Generate medicine ID
                    medicine_id = generate_medicine_id(medicine_name)
                    
                    # Prepare data
                    mrp = float(row["mrp"])
                    discount_percent = row.get("discount_percent", "")
                    if discount_percent == "":
                        discount_percent = None
                    else:
                        discount_percent = float(discount_percent)
                    
                    final_selling_price = calculate_final_selling_price(mrp, discount_percent)
                    
                    # Parse precautions
                    precautions_str = row.get("precautions", "")
                    precautions_json = parse_precautions(precautions_str)
                    
                    # Get prescription required flag
                    prescription_required = row.get("prescription_required", "false").lower()
                    if prescription_required not in ["true", "false"]:
                        prescription_required = "false"
                    
                    # Create medicine object
                    new_medicine = CoreMedicine(
                        medicine_id=medicine_id,
                        medicine_name=medicine_name,
                        medicine_category=medicine_category,
                        medicine_quantity=row["medicine_quantity"],
                        mrp=mrp,
                        discount_percent=discount_percent,
                        final_selling_price=final_selling_price,
                        medicine_description=row.get("medicine_description", "") or None,
                        medicine_composition=row.get("medicine_composition", "") or None,
                        precautions=precautions_json if precautions_json else None,
                        prescription_required=prescription_required,
                        medicine_photo=None
                    )
                    
                    medicines_batch.append(new_medicine)
                    existing_medicines.add((medicine_name, medicine_category))
                    
                    results["successful"] += 1
                    results["created_medicines"].append({
                        "medicine_id": medicine_id,
                        "medicine_name": medicine_name
                    })
                    
                    # Commit batch
                    if len(medicines_batch) >= batch_size:
                        db.add_all(medicines_batch)
                        db.commit()
                        medicines_batch = []
                
                except Exception as e:
                    results["failed"] += 1
                    results["successful"] -= 1  # Revert the count
                    results["created_medicines"].pop()  # Remove from created list
                    results["errors"].append(f"Row {row_num}: {str(e)}")
        
        # Commit remaining medicines
        if medicines_batch:
            db.add_all(medicines_batch)
            db.commit()
        
        return results
    
    except Exception as e:
        db.rollback()
        results["errors"].append(f"Error reading CSV file: {str(e)}")
        return results
