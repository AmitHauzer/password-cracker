
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class EnumStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    completed = "completed"
    failed = "failed"


class MinionRegistration(BaseModel):
    minion_id: str
    host: str
    port: int
    capabilities: List[str]


class HashTask(BaseModel):
    hash_value: str
    status: EnumStatus = EnumStatus.pending
    assigned_to: Optional[str] = None
    result: Optional[str] = None


class DisconnectRequest(BaseModel):
    minion_id: str
