from __future__ import annotations
import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, AnyHttpUrl
from cracker.master.client import fanout

log = logging.getLogger(__name__)
app = FastAPI(title="Password-cracking master v0")

# read minion URLs once at startup from env var
MINION_URLS: list[str] = [
    x.strip() for x in os.getenv("MINION_URLS", "").split(",") if x.strip()
]
if not MINION_URLS:
    log.warning("MINION_URLS env var is empty – master cannot delegate work.")


class CrackRequest(BaseModel):
    hash: str = Field(..., examples=["fd56081d9df7a238c52d7398fe1ed72f"])


class CrackResponse(BaseModel):
    found: bool
    password: str | None = None


@app.post("/crack", response_model=CrackResponse)
async def crack(req: CrackRequest):
    if not MINION_URLS:
        raise HTTPException(status_code=500, detail="No minions configured")

    log.info("Received crack request, delegating to %d minions", len(MINION_URLS))
    pwd = await fanout(MINION_URLS, req.hash)
    return CrackResponse(found=pwd is not None, password=pwd)
