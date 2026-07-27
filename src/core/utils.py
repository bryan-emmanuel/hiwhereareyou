import re
import hashlib

def format_phone_number(phone: str) -> str:
    """
    Standardizes a phone number to an E.164-like format (e.g. +15551234567).
    - Removes all non-numeric characters except initial '+'.
    - Replaces leading '00' with '+'.
    - If 10 digits, assumes US/Canada (+1).
    - If 11 digits starting with 1, assumes +1.
    - Otherwise, ensures there is a leading '+'.
    """
    # Keep only digits and initial '+' if present
    cleaned = re.sub(r'(?<!^)\+|[^\d+]', '', phone.strip())
    
    # Replace leading '00' with '+'
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
        
    # Standard 10-digit US/Canada number
    if len(cleaned) == 10 and cleaned.isdigit():
        cleaned = "+1" + cleaned
        
    # 11-digit starting with 1 (US number without '+')
    if len(cleaned) == 11 and cleaned.startswith("1") and cleaned.isdigit():
        cleaned = "+" + cleaned
        
    # Ensure there's a leading '+' if it is purely numeric
    if not cleaned.startswith("+") and cleaned.isdigit():
        cleaned = "+" + cleaned
        
    return cleaned

def calculate_parameter_hash(salt: str, location_id: str, player_id: str) -> str:
    """
    Calculates the secure 16-character parameter hash for player-specific progression validation:
    hash = SHA256(salt + location_id + player_id)[:16]
    """
    data = f"{salt}{location_id}{player_id}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]
