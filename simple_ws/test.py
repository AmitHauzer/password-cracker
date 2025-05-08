"""
Test script to send messages to minions.
"""

import asyncio
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_minions():
    """Test sending messages to all minions."""
    async with httpx.AsyncClient() as client:
        # First get list of connected minions
        response = await client.get("http://localhost:8000/minions")
        minions = response.json()["minions"]

        if not minions:
            logger.error("No minions connected")
            return

        logger.info(f"Found {len(minions)} minions: {minions}")

        # Send a test message to each minion
        for minion_id in minions:
            message = f"Hello, minion {minion_id}!"
            response = await client.post(
                f"http://localhost:8000/send/{minion_id}",
                params={"message": message}
            )
            logger.info(f"Sent message to minion {minion_id}: {message}")
            logger.info(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_minions())
