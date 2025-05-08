from __future__ import annotations
import hashlib
import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------


def phone_iter(prefix: str = "05") -> Iterator[str]:
    if len(prefix) != 2 or not prefix.isdigit():
        raise ValueError("prefix must be two digits, e.g. '05'")
    for num in range(100_000_000):
        yield f"{prefix}{num:08d}"

# ---------------------------------------------------------------------------


def md5_of(text: str) -> str:
    digest = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
    logger.debug(f"md5_of('{text}') -> {digest}")
    return digest

# ---------------------------------------------------------------------------


def crack_range(target_hash: str, start: int, end: int, prefix: str = "05") -> Optional[str]:
    if not 0 <= start <= end <= 99_999_999:
        raise ValueError("range must be within 0–99 999 999")

    logger.info(
        f"Cracking {start:08d}-{end:08d} with prefix {prefix} "
        f"against {target_hash[:8]}…"
    )

    for num in range(start, end + 1):
        candidate = f"{prefix}{num:08d}"
        logger.debug(f"{candidate=}")
        if md5_of(candidate) == target_hash:
            logger.info(f"Found match: {candidate}")
            return candidate

    logger.info(f"No match in {start:08d}-{end:08d}")
    return None
