
from config import parse_args, setup_logger, MASTER_SERVER_URL
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import uvicorn


args = parse_args("Password Cracker Minion Server")

logger = setup_logger("minion_server", log_level=args.log_level)

# Create FastAPI app
app = FastAPI(title="Password Cracker Minion Server")

minion_id = f"minion-{args.port}"


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
