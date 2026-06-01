import os
from uuid import uuid4

def save_file(file, upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid4()}_{file.filename}"
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path
