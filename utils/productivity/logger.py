import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_logger(name: str = __name__):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_fmt)
    
    # File handler with rotation (logs/app.log, 10MB max, 5 backups)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(message)s'
    )
    file_handler.setFormatter(file_fmt)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)  # Capture all, filter per logger if needed
    logger.propagate = False
    
    return logger


