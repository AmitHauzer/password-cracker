"""
Minion server for password cracking.
"""

import logging
import httpx
import uvicorn
import asyncio
import hashlib
import uuid
import argparse
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# Parse command line arguments
parser = argparse.ArgumentParser(description='Start a minion server')
parser.add_argument('--port', type=int, required=True,
                    help='Port to run the server on')
args = parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
MASTER_URL = "http://localhost:8000"
MINION_ID = f"minion-{args.port}"
HEARTBEAT_INTERVAL = 5  # seconds
REQUEST_TIMEOUT = 300.0  # 5 minutes timeout for requests
LOG_INTERVAL = 10000  # Log every 10,000 attempts
CHUNK_SIZE = 1000  # Process numbers in chunks for better performance

# Global variables
app = FastAPI()
is_registered = False
current_task = None
current_progress = 0
attempts = 0


class CrackRequest(BaseModel):
    """Request model for cracking a hash."""
    hash: str
    start: int
    end: int


class CrackResponse(BaseModel):
    """Response model for cracking a hash."""
    status: str
    password: Optional[str] = None
    error: Optional[str] = None


def _format_phone(number: int) -> str:
    """Format a number as a phone number."""
    return f"050-{number:07d}"


async def process_chunk(start: int, end: int, target_hash: str) -> Optional[str]:
    """Process a chunk of numbers sequentially."""
    for number in range(start, end):
        phone = _format_phone(number)
        hash_value = hashlib.md5(phone.encode()).hexdigest()
        if number % 100000 == 0:  # Log every 100,000 attempts
            logger.info(f"Trying phone number: {phone}")
        if hash_value == target_hash:
            logger.info(f"Found match! Phone: {phone}, Hash: {hash_value}")
            return phone
    return None


async def register_with_master():
    """Register this minion with the master server."""
    global is_registered
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MASTER_URL}/register/{MINION_ID}",
                params={"port": args.port},
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                is_registered = True
                logger.info(
                    f"Successfully registered with master as {MINION_ID}")
            else:
                logger.error(
                    f"Failed to register with master: {response.status_code}")
    except Exception as e:
        logger.error(f"Error registering with master: {e}")


async def send_heartbeat():
    """Send heartbeat to master server."""
    while True:
        try:
            if is_registered:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{MASTER_URL}/heartbeat/{MINION_ID}",
                        timeout=REQUEST_TIMEOUT
                    )
                    if response.status_code != 200:
                        logger.warning(
                            f"Heartbeat failed: {response.status_code}")
                        await register_with_master()
            else:
                await register_with_master()
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            await register_with_master()
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@app.on_event("startup")
async def startup_event():
    """Start heartbeat on startup."""
    logger.info(f"Starting minion server on port {args.port}")
    asyncio.create_task(send_heartbeat())


@app.post("/crack", response_model=CrackResponse)
async def crack_hash(request: CrackRequest):
    """Crack a hash in the given range."""
    global current_task, current_progress, attempts
    logger.info(
        f"Received crack request for hash {request.hash} in range {request.start:,}-{request.end:,}")

    current_task = request.hash
    current_progress = 0
    attempts = 0
    start_time = datetime.now()

    try:
        # Process the range sequentially in smaller chunks
        chunk_size = 10000  # Process 10,000 numbers at a time
        total_numbers = request.end - request.start + 1
        num_chunks = (total_numbers + chunk_size - 1) // chunk_size

        logger.info(f"Processing {num_chunks} chunks sequentially")

        for i in range(num_chunks):
            chunk_start = request.start + (i * chunk_size)
            chunk_end = min(chunk_start + chunk_size, request.end + 1)

            result = await process_chunk(chunk_start, chunk_end, request.hash)
            attempts += chunk_end - chunk_start
            current_progress = int((i + 1) * 100 / num_chunks)

            if (i + 1) % (num_chunks // 10) == 0 or i == num_chunks - 1:  # Log every 10% progress
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = attempts / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Progress: {current_progress}% | "
                    f"Attempts: {attempts:,} | "
                    f"Rate: {rate:.2f} hashes/sec | "
                    f"Elapsed: {elapsed:.1f}s | "
                    f"Current range: {chunk_start:,}-{chunk_end:,}"
                )

            if result:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"Found password for hash {request.hash}: {result} | "
                    f"Total attempts: {attempts:,} | "
                    f"Time: {elapsed:.2f} seconds"
                )
                current_task = None
                current_progress = 0
                return CrackResponse(status="success", password=result)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"No password found for hash {request.hash} in range {request.start:,}-{request.end:,} | "
            f"Total attempts: {attempts:,} | "
            f"Time: {elapsed:.2f} seconds"
        )
        current_task = None
        current_progress = 0
        return CrackResponse(status="not_found", error="Password not found in range")
    except Exception as e:
        logger.error(f"Error cracking hash: {e}")
        current_task = None
        current_progress = 0
        return CrackResponse(status="error", error=str(e))


@app.get("/status")
async def get_status():
    """Get minion status."""
    logger.debug("Status request received")
    return {
        "minion_id": MINION_ID,
        "port": args.port,
        "is_registered": is_registered,
        "current_task": current_task,
        "progress": current_progress,
        "attempts": attempts
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port)
