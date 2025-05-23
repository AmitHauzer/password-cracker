
"""Schemas for API responses."""

from pydantic import BaseModel


class GetTaskResponse(BaseModel):
    """Get task response.

    task_id:    The ID of the task.
    hash_value: The hash value to crack.
    start:      The start of the range to crack.
    end:        The end of the range to crack.
    start_str:  The start of the range to crack in string format.
    end_str:    The end of the range to crack in string format.
    """
    task_id:    str
    hash_value: str
    start:      int
    end:        int
    start_str:  str
    end_str:    str
