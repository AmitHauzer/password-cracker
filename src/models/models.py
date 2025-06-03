"""
Models for the master server.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """
    Status of a hash task.

        PENDING:    The task is pending.\n
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
    """
    Hash task request.

        hash_value: The hash value to crack.\n
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


class MinionStatus(str, Enum):
    """
    Status of a minion.

        CONNECCTED:   The minion is connected.\n
        DISCONNECTED: The minion is disconnected.
        BUSY:         The minion is busy processing a task.
    """
    CONNECCTED = "connected"
    DISCONNECTED = "disconnected"
    BUSY = "busy"


class Minion(BaseModel):
    """
    Minion model.

        minion_id:      The ID of the minion.\n
        host:           The host of the minion.
        port:           The port of the minion.
        capabilities:   The capabilities of the minion.
        status:         The status of the minion.
        registered_at:  The datetime when the minion was registered.
        last_heartbeat: The last heartbeat received from the minion.
    """
    minion_id: str
    host: str
    port: int
    capabilities: List[str]
    status: MinionStatus = MinionStatus.CONNECCTED
    registered_at: datetime
    last_heartbeat: Optional[datetime] = None
