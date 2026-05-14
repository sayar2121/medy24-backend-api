def generate_term_id() -> str:
    """
    Generate a unique term ID
    
    Returns:
        str: Generated term ID in format "TERM-{timestamp}"
    """
    import time
    
    # Create timestamp
    timestamp = int(time.time() * 1000)
    
    # Combine to create ID
    term_id = f"TERM-{timestamp}"
    
    return term_id
