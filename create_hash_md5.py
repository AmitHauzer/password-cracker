import hashlib

phone_numbers: list[str] = [
    "050-0000000",
    "050-0100000",
    "052-0000033",
    "051-2345678",
    "055-5555555",
    "057-5555559",
    "058-9123999",
    "059-9999999",
]


def get_hash(phone_number: str) -> str:
    """Generate MD5 hash for a phone number.

    Args:
        phone_number: Phone number in format '05X-XXXXXXX'

    Returns:
        MD5 hash of the phone number as a hexadecimal string
    """
    hash_obj = hashlib.md5(phone_number.encode())
    return hash_obj.hexdigest()


with open("hashes.txt", "w") as f:
    for phone_number in phone_numbers:
        hash_value = get_hash(phone_number)
        print(f"{phone_number} -> {hash_value}")
        f.write(f"{hash_value}\n")
