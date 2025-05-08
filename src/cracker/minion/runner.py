"""
CLI helper so you can just run:
    python -m cracker.minion.runner  --host 0.0.0.0  --port 8001
(and still keep `uvicorn` as the real server process).
"""
from __future__ import annotations
import uvicorn
import argparse
from minion_api import app


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8001)
    p.add_argument("--workers", type=int, default=1,
                   help="For CPU-bound work keep this at 1; "
                        "we’ll add multiproc later")
    args = p.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, workers=args.workers)


if __name__ == "__main__":
    main()
