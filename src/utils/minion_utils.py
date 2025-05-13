
"""Minion utilities."""


from hashlib import md5

from fastapi.logger import logger
import httpx

from config import FORMATTER_TASK_NAME, MASTER_SERVER_URL
from formatters import FORMATTERS
from models.schemas.request import SubmitResultRequest


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
    for candidate in range(start, end + 1):
        fmt = FORMATTERS[FORMATTER_TASK_NAME]
        phone_str = fmt.number_to_string(candidate)
#
        # every N attempts (or time), check if we should stop:
        if candidate % 1000 == 0:
            if not await should_continue(task_id):
                logger.info(f"Task {task_id} cancelled—stopping early.")
                return  # exit the loop
#
        if md5(phone_str.encode()).hexdigest() == hash_value:
            # found it—report and return
            await submit_result(minion_id, task_id, phone_str)
            return
    # exhausted slice, report no result
    await submit_result(minion_id, task_id, "")
