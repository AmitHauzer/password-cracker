"""
Utility functions for the master server.
"""

from asyncio.log import logger
from http.client import HTTPException
from pathlib import Path
from typing import Generator
from fastapi import UploadFile


def get_hash_from_file(file_path: Path) -> Generator[str, None, None]:
    """Helper function to read hashes from a file and yield them."""
    if not file_path.suffix == ".txt":
        raise HTTPException(
            status_code=400, detail=f"File must be a text file. the current file is: {file_path}")

    with open(file_path, 'r') as f:
        for line in f:
            if line == "" or line.startswith("#"):
                continue
            hash_value = line.strip()
            if hash_value:
                yield hash_value


async def save_temp_file(file: UploadFile) -> Path:
    """Save a file to the temporary directory."""
    temp_file = Path("temp_hashes.txt")
    content = await file.read()
    temp_file.write_bytes(content)
    return temp_file
