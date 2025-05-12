"""
Configuration for the password cracker.
"""

import argparse
from pathlib import Path
import sys
import logging

MASTER_SERVER_HOST = "localhost"
MASTER_SERVER_PORT = 8000
MASTER_SERVER_URL = f"http://{MASTER_SERVER_HOST}:{MASTER_SERVER_PORT}"

FORMATTER_TASK_NAME = "israel_phone"


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
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / file_name(name, port),
        encoding='utf-8'
    )
    file_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def parse_args(description: str) -> argparse.Namespace:
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
