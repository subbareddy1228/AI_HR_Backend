from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/downloads", tags=["Downloads"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(BASE_DIR)
DESKTOP_DIR = BASE_DIR / "static" / "downloads"


@router.get("/desktop")
def download_desktop_app():
    file_path = DESKTOP_DIR / "WorkPulseSetup 5.exe"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename="WorkPulseSetup 5.exe",
        media_type="application/octet-stream",
    )

