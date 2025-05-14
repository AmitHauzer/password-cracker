"""
Minion server for the password cracker.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

import asyncio
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from config import MINION_SERVER_LOGGER, parse_args, setup_logger, MASTER_SERVER_URL
from utils.minion_utils import process_task_response

args = parse_args("Password Cracker Minion Server")

logger = setup_logger(
    MINION_SERVER_LOGGER, log_level=args.log_level, port=args.port)

# Minion configuration
MINION_ID = f"minion-{args.port}"
MINION_HOST = args.host if args.host else "localhost"
MINION_PORT = args.port
MINION_CAPABILITIES = ["md5_crack"]  # Add more capabilities as needed
REQUEST_TIMEOUT = 10
HEARTBEAT_INTERVAL = 5
FETCH_TASKS_INTERVAL = 5

is_registered = False


async def register_to_master() -> bool:
    """Register this minion with the master server."""
    global is_registered
    try:
        async with httpx.AsyncClient() as client:
            req = {"minion_id": MINION_ID, "host": MINION_HOST,
                   "port": MINION_PORT, "capabilities": MINION_CAPABILITIES}
            logger.debug(f"register_to_master request details: {req}")

            response = await client.post(f"{MASTER_SERVER_URL}/register", json={**req}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            if response.status_code == 200:
                is_registered = True
                logger.info(
                    f"Successfully registered with master server as {MINION_ID}")
                return True
            return False
    except Exception as e:
        is_registered = False
        logger.error(f"Failed to register with master server: {str(e)}")
        return False


async def send_heartbeat() -> None:
    """Send heartbeat to master server."""
    while True:
        try:
            if is_registered:
                logger.info(
                    f"Sending heartbeat to master at {MASTER_SERVER_URL} from minion {MINION_ID}")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{MASTER_SERVER_URL}/minions/{MINION_ID}/heartbeat",
                        timeout=REQUEST_TIMEOUT
                    )
                    if response.status_code != 200:
                        logger.warning(
                            f"Heartbeat failed: {response.status_code}")
                        await register_to_master()
            else:
                await register_to_master()
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            await register_to_master()
        await asyncio.sleep(HEARTBEAT_INTERVAL)


async def disconnect_from_master() -> None:
    """Disconnect from the master server."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{MASTER_SERVER_URL}/disconnect-minion", json={"minion_id": MINION_ID})
        logger.info(f"Disconnected from master server as minion {MINION_ID}")


async def fetch_task_from_master(minion_id: str, minion_registered: bool, poll_interval: float = 5.0) -> None:
    """Fetch tasks from the master server."""
    async with httpx.AsyncClient() as client:
        logger.info(f"Fetching tasks loop for minion {minion_id}")
        while minion_registered:
            try:
                try:
                    resp = await client.get(
                        f"{MASTER_SERVER_URL}/get-task",
                        params={"minion_id": minion_id},
                    )
                except httpx.RequestError:
                    logger.warning("Cannot reach master; stopping fetch loop.")
                    await asyncio.sleep(poll_interval)
                    continue

                if not await process_task_response(resp, minion_id):
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error("Error fetching task:", exc_info=e)
                await asyncio.sleep(poll_interval)
                continue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan events for the application."""
    # Startup
    logger.info(f"Minion {MINION_ID} is starting")
    is_registered = await register_to_master()
    if is_registered:
        task_heartbeat = asyncio.create_task(send_heartbeat())
        task_fetch_tasks = asyncio.create_task(
            fetch_task_from_master(MINION_ID, is_registered, FETCH_TASKS_INTERVAL))
    yield
    # Shutdown
    if is_registered:
        task_heartbeat.cancel()
        task_fetch_tasks.cancel()
    await disconnect_from_master()
    logger.info("Shutting down minion server")


# Create FastAPI app with lifespan
app = FastAPI(title="Password Cracker Minion Server", lifespan=lifespan)


@app.get("/")
async def root() -> RedirectResponse:
    """Redirect to the docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check."""
    return {"status": "active"}


if __name__ == "__main__":
    uvicorn.run(app, host=MINION_HOST, port=MINION_PORT,
                log_level=args.log_level)
