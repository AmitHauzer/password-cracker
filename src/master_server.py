"""
Master server for the password cracker.
"""

from typing import Any, Dict, List, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Response, UploadFile, File, HTTPException, Query
from fastapi.responses import RedirectResponse

from config import FORMATTER_TASK_NAME, MASTER_SERVER_HOST, MASTER_SERVER_PORT, setup_logger, parse_args
from models.models import HashTask, TaskStatus
from models.schemas.request import DisconnectRequest, MinionRegistrationRequest, SubmitResultRequest
from models.schemas.response import GetTaskResponse
from utils.master_utils import get_hash_from_file, save_temp_file, split_range
from formatters import FORMATTERS


# Parse command line arguments
args = parse_args("Password Cracker Master Server")

logger = setup_logger("master_server", log_level=args.log_level)

# Create FastAPI app
app = FastAPI(title="Password Cracker Master Server")

# Store registered minions
minions: Dict[str, dict] = {}

# Store tasks
tasks: Dict[str, HashTask] = {}


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.post("/register")
async def register_minion(minion: MinionRegistrationRequest) -> Dict[str, str]:
    """Register a new minion server."""
    if minion.minion_id in minions:
        logger.warning(
            f"Minion {minion.minion_id} already registered. Updating registration.")
        # Update existing minion's information
        minions[minion.minion_id].update({
            "host": minion.host,
            "port": minion.port,
            "capabilities": minion.capabilities,
            "status": "active",
            "registered_at": datetime.now()
        })
    else:
        # Register new minion
        minions[minion.minion_id] = {
            "host": minion.host,
            "port": minion.port,
            "capabilities": minion.capabilities,
            "status": "active",
            "registered_at": datetime.now()
        }

    logger.info(
        f"Minion {minion.minion_id} registered successfully at {minion.host}:{minion.port}")
    return {"status": "success", "message": f"Minion {minion.minion_id} registered successfully"}


@app.post("/disconnect-minion")
async def disconnect_minion(req: DisconnectRequest) -> Dict[str, str]:
    """Disconnect a minion from the master server."""
    if req.minion_id not in minions:
        raise HTTPException(status_code=404, detail="Minion not registered")

    minions[req.minion_id]["status"] = "disconnected"
    logger.info(
        f"Minion {req.minion_id} disconnected successfully")
    return {"status": "success"}


@app.get("/minions")
async def list_minions() -> Dict[str, List[Dict[str, Any]]]:
    """List all registered minions."""
    return {
        "minions": [
            {
                "minion_id": mid,
                "host": data["host"],
                "port": data["port"],
                "status": data["status"],
                "capabilities": data["capabilities"]
            }
            for mid, data in minions.items()
        ]
    }


@app.post("/minions/{minion_id}/heartbeat")
async def minion_heartbeat(minion_id: str) -> Dict[str, str]:
    """Update minion heartbeat."""
    if minion_id not in minions:
        raise HTTPException(
            status_code=404, detail=f"Minion {minion_id} not found")

    minions[minion_id]["last_heartbeat"] = datetime.now()
    minions[minion_id]["status"] = "active"
    return {"status": "success"}


@app.post("/upload-hashes")
async def upload_hashes(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a file containing MD5 hashes."""
    try:
        # TODO: check if the the master server is already processing a file
        # TODO: if so, return a message that the server is busy

        # Save the uploaded file temporarily
        temp_file = await save_temp_file(file)
        fmt = FORMATTERS[FORMATTER_TASK_NAME]
        numeric_slices = split_range(
            fmt.min_value, fmt.max_value, len(minions))

        # Process hashes and create tasks
        for hash_value in get_hash_from_file(temp_file):
            logger.info(f"master got hash: {hash_value}")
            for idx, (start, end) in enumerate(numeric_slices):
                task_id = f"{hash_value}_{idx}"
                tasks[task_id] = HashTask(
                    hash_value=hash_value,
                    start=start,
                    end=end
                )
                logger.info(f"Created task {task_id}: {start}–{end}")

        # clean up
        temp_file.unlink()

        return {"status": "success", "message": f"Processed {len(tasks)} hashes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-task",
         response_model=GetTaskResponse,
         responses={204: {"description": "No tasks available"}})
async def get_task(minion_id: str) -> Union[GetTaskResponse, Response]:
    """Get a task for a minion to process."""
    if minion_id not in minions:
        raise HTTPException(status_code=404, detail="Minion not registered")

    # Find an unassigned task
    for task_id, task in tasks.items():
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = minion_id
            fmt = FORMATTERS[FORMATTER_TASK_NAME]
            return GetTaskResponse(task_id=task_id,
                                   hash_value=task.hash_value,
                                   start=task.start,
                                   end=task.end,
                                   start_str=fmt.number_to_string(task.start),
                                   end_str=fmt.number_to_string(task.end),
                                   )

    return Response(status_code=204)


@app.get("/task-status")
async def task_status(task_id: str = Query(..., description="ID of the task to check")) -> Dict[str, str]:
    """
    Return the current status of a given task_id.
    """
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": task.status.value}


@app.get("/all-tasks")
async def all_tasks() -> Dict[str, Dict[str, Any]]:
    """
    Return the full in-memory tasks dict, keyed by task_id.
    Each value includes hash_value, start/end, status, assigned_to, result.
    """
    # Convert each HashTask into a plain dict for JSON serialization
    return {
        "tasks": {
            task_id: task.model_dump()
            for task_id, task in tasks.items()
        }
    }


@app.post("/submit-result")
async def submit_result(req: SubmitResultRequest) -> Dict[str, Any]:
    """Submit a result from a minion."""
    # 1) Validate minion
    if req.minion_id not in minions:
        raise HTTPException(404, "Minion not registered")

    # 2) Validate task
    task = tasks.get(req.task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.assigned_to != req.minion_id:
        raise HTTPException(400, "Task not assigned to this minion")

    # 3) Update this task
    if req.result:
        task.status = TaskStatus.COMPLETED
        task.result = req.result
        # 4) Cancel all other slices for the same hash
        hash_val = task.hash_value
        for other_id, other in tasks.items():
            if (other.hash_value == hash_val) and (other_id != req.task_id):
                if other.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
                    other.status = TaskStatus.CANCELLED
    else:
        # no result found in this slice
        task.status = TaskStatus.CANCELLED

    return {"status": "success", "task_id": req.task_id, "new_status": task.status.value}


@app.get("/status")
async def get_status() -> Dict[str, Dict[str, Any]]:
    """Get the current status of all tasks and minions."""
    return {
        "minions": minions,
        "tasks": {k: v.model_dump() for k, v in tasks.items()}
    }

if __name__ == "__main__":
    uvicorn.run(app, host=MASTER_SERVER_HOST,
                log_level=args.log_level, port=MASTER_SERVER_PORT)
