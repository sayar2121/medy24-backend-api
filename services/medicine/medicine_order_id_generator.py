import time


def generate_order_id(customer_id: str, shop_id: str = None) -> str:
    """
    Generate a unique order ID using customer ID, pharmacy shop ID, and timestamp.
    Format: ORD_<customer_id>_<shop_id>_<timestamp_ms>
    
    Args:
        customer_id: Customer ID
        shop_id: Pharmacy shop ID (optional, can be added later when shop accepts)
    
    Returns:
        str: Unique order ID
    
    Example: ORD_CUST123456_SHOP789012_1778920685126
    """
    timestamp = int(time.time() * 1000)
    
    if shop_id:
        order_id = f"ORD_{customer_id}_{shop_id}_{timestamp}"
    else:
        order_id = f"ORD_{customer_id}_{timestamp}"
    
    return order_id
