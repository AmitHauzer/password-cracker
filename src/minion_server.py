"""
Minion server for the password cracker.
"""

from contextlib import asynccontextmanager
from hashlib import md5
from typing import AsyncIterator, Dict

import asyncio
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from config import parse_args, setup_logger, MASTER_SERVER_URL, FORMATTER_TASK_NAME
from formatters import FORMATTERS
from models.schemas.request_schemas import SubmitResultRequest

args = parse_args("Password Cracker Minion Server")

logger = setup_logger(
    "minion_server", log_level=args.log_level, port=args.port)

# Minion configuration
MINION_ID = f"minion-{args.port}"
MINION_HOST = args.host if args.host else "localhost"
MINION_PORT = args.port
MINION_CAPABILITIES = ["md5_crack"]  # Add more capabilities as needed
REQUEST_TIMEOUT = 10
HEARTBEAT_INTERVAL = 5

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan events for the application."""
    # Startup
    logger.info(f"Minion {MINION_ID} is starting")
    is_registered = await register_to_master()
    if is_registered:
        asyncio.create_task(send_heartbeat())
    yield
    # Shutdown
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


async def should_continue(task_id: str) -> bool:
    """
    Ask the master if this task is still assigned.
    Returns False if status is 'cancelled' or 'completed'.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{MASTER_SERVER_URL}/task-status",
            params={"task_id": task_id},
            timeout=5.0
        )

    r.raise_for_status()
    status = r.json()["status"]
    return status == "assigned"


async def crack_range(task_id: str, hash_value: str, start: int, end: int) -> None:
    """Crack a range of numbers."""
    for candidate in range(start, end + 1):
        fmt = FORMATTERS[FORMATTER_TASK_NAME]
        phone_str = fmt.number_to_string(candidate)

        # every N attempts (or time), check if we should stop:
        if candidate % 1000 == 0:
            if not await should_continue(task_id):
                logger.info(f"Task {task_id} cancelled—stopping early.")
                return  # exit the loop

        if md5(phone_str.encode()).hexdigest() == hash_value:
            # found it—report and return
            await submit_result(MINION_ID, task_id, phone_str)
            return
    # exhausted slice, report no result
    await submit_result(MINION_ID, task_id, "")


async def submit_result(minion_id: str, task_id: str, result: str) -> None:
    """Submit a result to the master server."""
    payload = SubmitResultRequest(
        minion_id=minion_id,
        task_id=task_id,
        result=result
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{MASTER_SERVER_URL}/submit-result",
            json=payload.model_dump()
        )

if __name__ == "__main__":
    uvicorn.run(app, host=MINION_HOST, port=MINION_PORT,
                log_level=args.log_level)
