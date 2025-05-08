"""
Shared data models for the password cracker service.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a cracking task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PhoneRange(BaseModel):
    """Range of phone numbers to check."""
    start: str = Field(..., pattern=r"^05\d-\d{7}$")
    end: str = Field(..., pattern=r"^05\d-\d{7}$")


class CrackRequest(BaseModel):
    """Request to crack a hash."""
    hash: str = Field(..., min_length=32, max_length=32)
    range: PhoneRange


class CrackResponse(BaseModel):
    """Response from a cracking attempt."""
    status: TaskStatus
    password: Optional[str] = None
    error: Optional[str] = None


class MinionStatus(BaseModel):
    """Status of a minion server."""
    id: str
    status: TaskStatus
    current_task: Optional[CrackRequest] = None
    last_heartbeat: float
