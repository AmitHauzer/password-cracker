
"""Minion utilities."""


from hashlib import md5

from logging import getLogger
import httpx

from config import FORMATTER_TASK_NAME, MASTER_SERVER_URL, MINION_SERVER_LOGGER
from formatters import FORMATTERS
from models.schemas.request import SubmitResultRequest

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
    logger.info(
        f"[{task_id}] Starting crack: hash={hash_value},range={start}-{end}")

    fmt = FORMATTERS[FORMATTER_TASK_NAME]
    total = end - start + 1
    tried = 0
    percent_checkpoint = max(total // 10, 1)  # every 10%

    for candidate in range(start, end + 1):
        tried += 1

        phone_str = fmt.number_to_string(candidate)

        # every 10% of the range, log progress
        if tried % percent_checkpoint == 0:
            pct = (tried / total) * 100
            logger.info(
                f"[{task_id}] Progress: {tried}/{total}, ({pct:.1f}%) — last={phone_str}")

        # every N attempts (or time), check if we should stop:
        if candidate % 1000 == 0:
            if not await should_continue(task_id):
                logger.info(f"Task {task_id} cancelled—stopping early.")
                return  # exit the loop

        if md5(phone_str.encode()).hexdigest() == hash_value:
            # found it—report and return
            logger.info(
                f"[{task_id}] - FOUND Password: {phone_str}.")
            await submit_result(minion_id, task_id, phone_str)
            return

    # exhausted slice, report no result
    logger.info(
        f"[{task_id}] - NO MATCH found in range ({start}, {end + 1})")
    await submit_result(minion_id, task_id, "")
