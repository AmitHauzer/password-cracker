"""
Configuration for the password cracker.
"""

import argparse
from pathlib import Path
import sys
import logging

# Master server configuration
MASTER_SERVER_HOST = "localhost"
MASTER_SERVER_PORT = 8000
MASTER_SERVER_URL = f"http://{MASTER_SERVER_HOST}:{MASTER_SERVER_PORT}"

# Minion server configuration
MASTER_SERVER_LOGGER = "master_server"
MINION_SERVER_LOGGER = "minion_server"

# Task configuration
FORMATTER_TASK_NAME = "israel_phone"
TASKS_DB_FILE = Path("tasks_db.json")
LOG_DIR = Path("logs")
LOG_PROGRESS_INTERVAL = 100_000  # for cracking progress
CANCEL_CHECK_INTERVAL = 10_000   # for checking if minion should stop


def file_name(name: str, port: int | None = None) -> str:
    if "minion" in name:
        return f"minion_{port}.log"
    return f"{name}.log"


def setup_logger(name: str, log_level: int = logging.INFO, port: int | None = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting and handlers.

    Args:
        name: The name of the logger
        log_level: The logging level (default: INFO)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Create file handler
    LOG_DIR.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        LOG_DIR / file_name(name, port),
        encoding='utf-8'
    )
    file_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def parse_args(description: str) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--log-level', type=str, default='info',
                        choices=['debug', 'info',
                                 'warning', 'error', 'critical'],
                        help='Log level to use')

    if "minion" in description.lower():
        parser.add_argument("--host", type=str,
                            help='Host to run the server on')
        parser.add_argument("--port", type=int, required=True,
                            help='Port to run the server on')

    args = parser.parse_args()
    args.log_level = getattr(logging, args.log_level.upper())

    return args
