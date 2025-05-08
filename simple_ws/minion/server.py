"""
Simple minion server that connects to master and echoes back messages.
"""

import asyncio
import logging
import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
minion_id = str(uuid.uuid4())
MASTER_URL = "ws://localhost:8000/ws"


async def connect_to_master():
    """Connect to master server with retry logic."""
    while True:
        try:
            async with websockets.connect(f"{MASTER_URL}/{minion_id}") as websocket:
                logger.info(f"Connected to master with ID: {minion_id}")

                while True:
                    try:
                        # Wait for message from master
                        message = await websocket.recv()
                        logger.info(f"Received message: {message}")

                        # Echo back the message
                        await websocket.send(f"Echo: {message}")
                        logger.info(f"Sent echo: {message}")

                    except websockets.exceptions.ConnectionClosed:
                        logger.info(
                            "Connection closed, attempting to reconnect...")
                        break
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        break

        except Exception as e:
            logger.error(f"Connection error: {e}")
            logger.info("Retrying connection in 5 seconds...")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start connection to master on startup."""
    asyncio.create_task(connect_to_master())

if __name__ == "__main__":
    args = parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
