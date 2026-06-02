import os
import shutil
from fastapi import UploadFile, HTTPException

from core.config import settings


def save_file(file: UploadFile, prefix: str) -> str:
    upload_dir = settings.upload_dir
    max_size_mb = settings.max_file_size_mb

    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Validate file size (UploadFile.size may be None)
    if file.size is not None:
        if file.size > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max allowed is {max_size_mb} MB"
            )

    file_path = os.path.join(upload_dir, f"{prefix}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path
