# utils/logger.py

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """Creates and returns a logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(f"{LOG_DIR}/{name}_{date_str}.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
