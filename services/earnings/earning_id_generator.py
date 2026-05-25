import time


def generate_earning_id(shop_id: str) -> str:
    """
    Generate a unique earning ID using pharmacy shop ID and timestamp.
    Format: EAR_<shop_id>_<timestamp_ms>
    
    Args:
        shop_id: Pharmacy shop ID
    
    Returns:
        str: Unique earning ID
    
    Example: EAR_SHOP789012_1778920685126
    """
    timestamp = int(time.time() * 1000)
    earning_id = f"EAR_{shop_id}_{timestamp}"
    
    return earning_id
