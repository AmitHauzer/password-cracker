
"""Minion utilities."""


from hashlib import md5

from logging import getLogger
import httpx
from pydantic import ValidationError

from config import CANCEL_CHECK_INTERVAL, FORMATTER_TASK_NAME, LOG_PROGRESS_INTERVAL, MASTER_SERVER_URL, MINION_SERVER_LOGGER
from formatters import FORMATTERS
from models.schemas.request import SubmitResultRequest
from models.schemas.response import GetTaskResponse

logger = getLogger(MINION_SERVER_LOGGER)


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


async def crack_range(minion_id: str, task_id: str, hash_value: str, start: int, end: int) -> None:
    """Crack a range of numbers."""

    fmt = FORMATTERS[FORMATTER_TASK_NAME]
    total = end - start + 1
    tried = 0

    logger.info(
        f"[{task_id}] - Starting crack: hash={hash_value},range={fmt.number_to_string(start)}-{fmt.number_to_string(end)}")

    for candidate in range(start, end + 1):
        tried += 1
        phone_str = fmt.number_to_string(candidate)

        if tried % LOG_PROGRESS_INTERVAL == 0:
            pct = (tried / total) * 100
            logger.info(
                f"[{task_id}] - Progress: ({pct:.1f}%) current={phone_str}")

        # every N attempts (or time), check if we should stop:
        if candidate % CANCEL_CHECK_INTERVAL == 0:
            if not await should_continue(task_id):
                logger.info(f"Task {task_id} cancelled—stopping early.")
                return  # exit the loop

        if md5(phone_str.encode()).hexdigest() == hash_value:
            # found it—report and return
            logger.info(
                f"[{task_id}] - FOUND Password!: password={phone_str}, hash={hash_value}")
            await submit_result(minion_id, task_id, phone_str)
            return

    # exhausted slice, report no result
    logger.info(
        f"[{task_id}] - NO MATCH found in range ({start}, {end + 1})")
    await submit_result(minion_id, task_id, "")


async def process_task_response(resp: httpx.Response, minion_id: str) -> bool:
    """Process a task response from the master server.
    Returns True if a task was processed, False if we should sleep and retry."""
    if resp.status_code == 204:
        logger.debug(f"No tasks available for minion {minion_id}")
        return False

    if resp.status_code != 200:
        logger.error(f"Unexpected status {resp.status_code} from get-task")
        return False

    try:
        task = GetTaskResponse(**resp.json())
    except (ValueError, ValidationError) as e:
        logger.error("Invalid GetTaskResponse payload", exc_info=e)
        return False

    await crack_range(
        minion_id=minion_id,
        task_id=task.task_id,
        hash_value=task.hash_value,
        start=task.start,
        end=task.end,
    )
    return True
