import time


def generate_cart_id():
    """
    Generate a unique cart ID using timestamp and customer identifier pattern.
    Format: CART + timestamp (milliseconds)
    Example: CART1778920685126
    """
    timestamp = int(time.time() * 1000)
    cart_id = f"CART{timestamp}"
    return cart_id
