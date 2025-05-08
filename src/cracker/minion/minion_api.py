from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cracker_core import crack_range

app = FastAPI(title="Password-cracking minion")

class CrackRequest(BaseModel):
    hash: str = Field(..., examples=["fd56081d9df7a238c52d7398fe1ed72f"])
    start: int = Field(..., ge=0, le=99_999_999)
    end:   int = Field(..., ge=0, le=99_999_999)

class CrackResponse(BaseModel):
    found: bool
    password: str | None = None


@app.post("/crack", response_model=CrackResponse)
def crack(req: CrackRequest):
    if req.start > req.end:
        raise HTTPException(status_code=400, detail="start must be ≤ end")
    pwd = crack_range(req.hash, req.start, req.end)
    return CrackResponse(found=pwd is not None, password=pwd)
