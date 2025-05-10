"""
Test script for password cracker.
"""

import asyncio
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cracker():
    """Test the password cracker."""
    async with httpx.AsyncClient() as client:
        # Get list of minions
        response = await client.get("http://localhost:8000/minions")
        minions = response.json()["minions"]

        if not minions:
            logger.error("No minions registered")
            return

        logger.info(f"Found minions: {minions}")

        # Test hash: "d41d8cd98f00b204e9800998ecf8427e" (MD5 of empty string)
        test_hash = "d41d8cd98f00b204e9800998ecf8427e"

        # Submit hash to crack
        response = await client.post(
            "http://localhost:8000/crack",
            json={"hash": test_hash}
        )
        logger.info(f"Crack request response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_cracker())
