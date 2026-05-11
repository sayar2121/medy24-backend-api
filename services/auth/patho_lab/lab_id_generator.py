from sqlalchemy.orm import Session
from sqlalchemy import func

def generate_lab_id(db: Session, model):
    last_user = db.query(model).order_by(model.id.desc()).first()
    if not last_user:
        return "LAB1000"
    
    last_id = last_user.lab_id
    try:
        # Extract the numeric part after 'LAB'
        number = int(last_id.replace("LAB", ""))
        new_number = number + 1
        return f"LAB{new_number}"
    except (ValueError, AttributeError):
        return "LAB1000"
