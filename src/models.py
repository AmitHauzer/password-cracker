"""
Models for the master server.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Status of a hash task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


class MinionRegistration(BaseModel):
    """Minion registration request."""
    minion_id: str
    host: str
    port: int
    capabilities: List[str]


class HashTask(BaseModel):
    """Hash task request."""
    hash_value: str
    start: int
    end: int
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    result: Optional[str] = None


class DisconnectRequest(BaseModel):
    """Disconnect request."""
    minion_id: str
