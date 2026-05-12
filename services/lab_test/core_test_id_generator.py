import time
import re

def generate_core_test_id(test_name: str) -> str:
    # Slugify the test name: lowercase, remove non-alphanumeric, replace spaces with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', test_name.lower()).strip('-')
    # Get current timestamp in milliseconds
    timestamp = int(time.time() * 1000)
    # Return formatted ID
    return f"TEST-{slug}-{timestamp}"
