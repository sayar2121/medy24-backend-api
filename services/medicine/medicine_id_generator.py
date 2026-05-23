def generate_medicine_id(medicine_name: str) -> str:
    """
    Generate a unique medicine ID based on medicine name and UUID
    
    Args:
        medicine_name: Name of the medicine
    
    Returns:
        str: Generated medicine ID in format "MED-{name_hash}-{random_uuid}"
    """
    import hashlib
    import uuid
    
    # Create hash from medicine name
    name_hash = hashlib.md5(medicine_name.encode()).hexdigest()[:4].upper()
    
    # Generate random UUID
    random_id = uuid.uuid4().hex[:8].upper()
    
    # Combine to create ID
    medicine_id = f"MED-{name_hash}-{random_id}"
    
    return medicine_id
