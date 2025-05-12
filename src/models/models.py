"""
Models for the master server.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Status of a hash task.

    PENDING:    The task is pending.
    ASSIGNED:   The task is assigned to a minion.
    COMPLETED:  The task is completed.
    FAILED:     The task failed.
    CANCELLED:  The task is cancelled.
    """
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HashTask(BaseModel):
    """Hash task request.

    hash_value: The hash value to crack.
    start:      The start of the range to crack.
    end:        The end of the range to crack.
    status:     The status of the task.
    assigned_to: The ID of the minion assigned to the task.
    """
    hash_value: str
    start: int
    end: int
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    result: Optional[str] = None
