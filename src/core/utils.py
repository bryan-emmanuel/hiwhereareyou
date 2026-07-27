import re

def format_phone_number(phone: str) -> str:
    """
    Standardizes a phone number to E.164 format.
    E.g., '+1 (555) 123-4567' -> '+15551234567'.
    Throws ValueError if the input phone number format is invalid.
    """
    cleaned = re.sub(r'[\s\-()]/g', '', phone.strip())
    # Remove any other non-digit, non-plus characters
    cleaned = re.sub(r'[^\d+]', '', cleaned)
    
    if not cleaned:
        raise ValueError("Empty phone number input")

    # If it has a plus sign, make sure it is at the beginning
    if "+" in cleaned:
        if not cleaned.startswith("+"):
            raise ValueError("Invalid phone number format: '+' must be at the start")
    else:
        # Default to US/Canada +1 if only 10 digits are provided
        if len(cleaned) == 10:
            cleaned = "+1" + cleaned
        elif cleaned.startswith("1") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        else:
            # Fallback prefix
            cleaned = "+" + cleaned

    # Check structure
    if not re.match(r'^\+\d{7,15}$', cleaned):
        raise ValueError("Invalid phone number digits count (must be E.164 compliant, 7 to 15 digits)")

    return cleaned
