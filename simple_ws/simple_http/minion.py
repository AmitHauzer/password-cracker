"""
Simple HTTP minion.
"""

import logging
import uuid
import time
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

minion_id = str(uuid.uuid4())
MASTER_URL = "http://localhost:8000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler."""
    # Startup
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{MASTER_URL}/register/{minion_id}")
            if response.status_code == 200:
                logger.info(f"Registered with master as {minion_id}")
            else:
                logger.error("Failed to register with master")
    except Exception as e:
        logger.error(f"Error registering with master: {e}")
    yield
    # Shutdown
    logger.info("Shutting down minion")

app = FastAPI(lifespan=lifespan)


@app.get("/message")
async def get_message():
    """Get a message from the master."""
    return {"message": "Hello from minion!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
