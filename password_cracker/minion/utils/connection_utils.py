"""
Connection utilities for minion to master communication.
"""

import logging
import httpx
from typing import Optional
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MASTER_URL = "http://localhost:8000"
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds


async def connect_to_master(minion_id: str) -> bool:
    """Attempt to connect to the master server.

    Args:
        minion_id: The ID of the minion trying to connect

    Returns:
        bool: True if connection successful, False otherwise
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{MASTER_URL}/register/{minion_id}")
                if response.status_code == 200:
                    logger.info(
                        f"Successfully registered with master as {minion_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to register with master: {response.status_code}")
        except Exception as e:
            logger.warning(f"Connection attempt {retries + 1} failed: {e}")

        retries += 1
        if retries < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)

    logger.error("Failed to connect to master after maximum retries")
    return False


async def send_heartbeat(minion_id: str) -> bool:
    """Send heartbeat to master server.

    Args:
        minion_id: The ID of the minion sending the heartbeat

    Returns:
        bool: True if heartbeat successful, False otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{MASTER_URL}/heartbeat/{minion_id}")
            if response.status_code == 200:
                return True
            logger.error(f"Heartbeat failed: {response.status_code}")
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
    return False
