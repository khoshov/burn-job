"""Centralized Logging Infrastructure for Performance Optimization Pipeline."""

import logging
import os
import sys
from typing import Optional
from burn_job.core.config import RUN_LOG_PATH

def setup_logger(name: str = "pipeline", log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a structured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    target_log_file = log_file or RUN_LOG_PATH
    if target_log_file:
        os.makedirs(os.path.dirname(target_log_file), exist_ok=True)
        fh = logging.FileHandler(target_log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
