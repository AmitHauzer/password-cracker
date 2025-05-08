"""
Simple HTTP master server.
"""

import logging
from fastapi import FastAPI, HTTPException
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Store registered minions
minions = set()


@app.post("/register/{minion_id}")
async def register_minion(minion_id: str):
    """Register a new minion."""
    minions.add(minion_id)
    logger.info(f"Minion {minion_id} registered")
    return {"status": "registered"}


@app.get("/minions")
async def get_minions():
    """Get list of registered minions."""
    return {"minions": list(minions)}


@app.post("/send/{minion_id}")
async def send_to_minion(minion_id: str, message: str):
    """Send a message to a specific minion."""
    if minion_id not in minions:
        raise HTTPException(status_code=404, detail="Minion not found")

    # In a real application, you would send this to the minion
    # For this example, we'll just log it
    logger.info(f"Message for minion {minion_id}: {message}")
    return {"status": "message sent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
