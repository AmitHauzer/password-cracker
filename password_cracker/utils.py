"""
Utility functions for password cracking.
"""

import hashlib
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_hash(phone: str) -> str:
    """Calculate MD5 hash of a phone number."""
    return hashlib.md5(phone.encode()).hexdigest()


def format_phone(number: int) -> str:
    """Format a number as a phone number (050-XXXXXXX)."""
    return f"050-{number:07d}"


def split_range(total_range: int, num_parts: int) -> list[Tuple[int, int]]:
    """Split a range into equal parts.

    Args:
        total_range: Total number of items to split
        num_parts: Number of parts to split into

    Returns:
        List of (start, end) tuples for each part
    """
    if num_parts < 1:
        raise ValueError("Number of parts must be at least 1")

    part_size = total_range // num_parts
    ranges = []

    for i in range(num_parts):
        start = i * part_size
        end = start + part_size if i < num_parts - 1 else total_range
        ranges.append((start, end))

    return ranges


def crack_password(start: int, end: int, target_hash: str) -> Optional[str]:
    """Crack a password in the given range.

    Args:
        start: Start of the range
        end: End of the range
        target_hash: Hash to find

    Returns:
        Found password or None if not found
    """
    for i in range(start, end):
        phone = format_phone(i)
        hash_value = calculate_hash(phone)
        if hash_value == target_hash:
            return phone
    return None


def verify_hash(phone: str, target_hash: str) -> bool:
    """Verify if a phone number matches the target hash."""
    return calculate_hash(phone) == target_hash
