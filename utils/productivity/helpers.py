from passlib.context import CryptContext
from datetime import datetime
import os
from app.core import config
from app.utils.s3 import upload_to_s3  #  NEW

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# Export Helpers (unchanged)

def ensure_export_dir():
    path = settings.EXPORT_DIR
    os.makedirs(path, exist_ok=True)
    return path


def make_export_filename(prefix: str, ext: str):
    dt = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{dt}.{ext}"



# Auth Helpers (unchanged)

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)



# File Upload (UPDATED → S3)

def save_file(file, upload_dir: str, filename: str = None):
    """
    Upload to S3 (legacy compat).
    """
    file.file.seek(0)
    return upload_to_s3(file, upload_dir)
