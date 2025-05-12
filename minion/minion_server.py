"""
Minion server for the password cracker.
"""
import asyncio
from contextlib import asynccontextmanager

import uvicorn
import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from config import parse_args, setup_logger, MASTER_SERVER_URL


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


async def send_heartbeat():
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


async def disconnect_from_master():
    """Disconnect from the master server."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{MASTER_SERVER_URL}/disconnect-minion", json={"minion_id": MINION_ID})
        logger.info(f"Disconnected from master server as minion {MINION_ID}")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    return {"status": "active"}


if __name__ == "__main__":
    uvicorn.run(app, host=MINION_HOST, port=MINION_PORT,
                log_level=args.log_level)
