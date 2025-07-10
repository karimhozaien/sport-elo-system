from unidecode import unidecode

def convert_special_to_regular(text):
    """Converts special characters (e.g., accented letters) to regular ASCII letters."""
    return unidecode(text)

def normalize_fighter_name(name):
    """Normalize a fighter name by converting special characters and making it lowercase."""
    # Convert special characters to regular ASCII
    normalized = convert_special_to_regular(name)
    # Convert to lowercase
    return normalized.lower()

# Example usage
if __name__ == "__main__":
    # Test cases
    test_names = [
        "Guimarães",
        "João",
        "José",
        "André",
        "César",
        "Miyao",
        "Galvão"
    ]
    
    for name in test_names:
        normalized = normalize_fighter_name(name)
        print(f"'{name}' -> '{normalized}'") 