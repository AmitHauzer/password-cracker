
"""Schemas for API requests."""

from pydantic import BaseModel


class SubmitResultRequest(BaseModel):
    """Submit result request.

    minion_id: The ID of the minion submitting the result.
    task_id:   The ID of the task being submitted.
    result:    The discovered password (empty string if none).
    """
    minion_id: str
    task_id:   str
    result:    str  # the discovered password (empty string if none)
