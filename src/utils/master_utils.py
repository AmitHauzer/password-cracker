"""
Utility functions for the master server.
"""
from pathlib import Path
from typing import Generator

from asyncio.log import logger
from fastapi import HTTPException
from fastapi import UploadFile


def get_hash_from_file(file_path: Path) -> Generator[str, None, None]:
    """Helper function to read hashes from a file and yield them."""

    with open(file_path, 'r') as f:
        for line in f:
            if line == "" or line.startswith("#"):
                continue
            hash_value = line.strip()
            if hash_value:
                yield hash_value


async def save_temp_file(file: UploadFile) -> Path:
    """Save a file to the temporary directory."""
    if not file.filename.endswith(".txt"):
        logger.error(
            f"File must be a text file. the current file is: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"File must be a text file. the current file is: {file.filename}"
        )

    temp_file = Path("temp_hashes.txt")
    content = await file.read()
    temp_file.write_bytes(content)
    return temp_file


def split_range(start: int, end: int, parts: int) -> list[tuple[int, int]]:
    """
    Divide [start..end] into `parts` contiguous slices.
    Handles remainders so that early slices get one extra item when needed.
    """
    total = end - start + 1
    base, rem = divmod(total, parts)

    slices = []
    current = start
    for i in range(parts):
        # give the first `rem` slices an extra element
        inc = base + (1 if i < rem else 0)
        s = current
        e = current + inc - 1
        slices.append((s, e))
        current = e + 1

    return slices
