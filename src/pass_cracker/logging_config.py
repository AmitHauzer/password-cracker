"""
Centralised logging setup for the whole project.

* Creates <project-root>/logs if missing.
* Adds a console handler (human-readable).
* Adds a daily-rotating file handler (ISO-8601 in filename).
* Must be called **once** early in your application
  (e.g. from `cracker.__init__` or main.py).

Usage
-----
    from cracker.logging_config import setup_logging
    setup_logging(level="DEBUG")           # optional level override
"""
from __future__ import annotations
import logging
import logging.handlers
import pathlib
from datetime import datetime
from typing import Literal, Optional

_LEVEL = {
    "CRITICAL": logging.CRITICAL,
    "ERROR":    logging.ERROR,
    "WARNING":  logging.WARNING,
    "INFO":     logging.INFO,
    "DEBUG":    logging.DEBUG,
}


def setup_logging(level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO", log_dir: Optional[pathlib.Path | str] = "logs",) -> None:
    log_dir = pathlib.Path(log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"cracker-{datetime.now():%Y-%m-%d}.log"

    root = logging.getLogger()

    root.setLevel(_LEVEL[level])

    fmt = "%(asctime)s - %(levelname)s - %(name)s: - %(message)s"
    datefmt = "%H:%M:%S"

    # ── console ────────────────────────────────────────────────────────────────
    con = logging.StreamHandler()
    con.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(con)

    # ── file (rotates at midnight, keeps 7 days) ───────────────────────────────
    file_h = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_h.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(file_h)
