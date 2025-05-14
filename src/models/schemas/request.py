
"""Schemas for API requests."""

from typing import List
from pydantic import BaseModel


class MinionRegistrationRequest(BaseModel):
    """Minion registration request.

    minion_id: The ID of the minion registering.
    host:      The host of the minion.
    port:      The port of the minion.
    capabilities: The capabilities of the minion.
    """
    minion_id: str
    host: str
    port: int
    capabilities: List[str]


class SubmitResultRequest(BaseModel):
    """Submit result request.

    minion_id: The ID of the minion submitting the result.
    task_id:   The ID of the task being submitted.
    result:    The discovered password (empty string if none).
    """
    minion_id: str
    task_id:   str
    result:    str  # the discovered password (empty string if none)


class DisconnectRequest(BaseModel):
    """Disconnect request.

    minion_id: The ID of the minion disconnecting.
    """
    minion_id: str
