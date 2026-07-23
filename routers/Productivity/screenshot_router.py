from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from utils.productivity.logger import get_logger

from pathlib import Path
import shutil
from typing import List
from datetime import datetime
from fastapi import Query
from core.dependencies import require_roles
from core.database import get_db
from model.Productivity.screenshot import Screenshot
from core.dependencies import get_current_user
from schema.Productivity.screenshot import ScreenshotResponse, ScreenshotPaginationResponse
from utils.productivity.s3 import upload_to_s3

logger = get_logger(__name__)

router = APIRouter(prefix="/screenshots")


@router.post("/", response_model=ScreenshotResponse)
def upload_screenshot(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    logger.info(f"Upload screenshot request for user_id={current_user.id}, filename={file.filename}")
    try:
        file_url = upload_to_s3(
        file,
        f"screenshots/employee_{current_user.id}/{datetime.utcnow().date()}"
    )

        screenshot = Screenshot(
            employee_id=current_user.id,
            department_id=current_user.department_id,
            image_path=file_url,
            timestamp=datetime.utcnow()
           
        )

        db.add(screenshot)
        db.commit()
        db.refresh(screenshot)
        logger.info(f"Screenshot uploaded successfully: id={screenshot.id}")
        return screenshot
    except Exception as e:
        logger.error(f"Error uploading screenshot for user_id={current_user.id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Screenshot upload failed")


@router.get(
    "/{employee_id}",
    response_model=ScreenshotPaginationResponse,
)
def get_employee_screenshots(
    employee_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(15, le=50),
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(["Admin"])),
):
    logger.info(f"Get screenshots for employee_id={employee_id}, page={page}, limit={limit}")
    offset = (page - 1) * limit

    rows = (
        db.query(Screenshot)
        .filter(Screenshot.employee_id == employee_id)
        .order_by(Screenshot.timestamp.desc())
        .offset(offset)
        .limit(limit + 1)  
        .all()
    )

    has_more = len(rows) > limit
    logger.info(f"Found {len(rows[:limit])} screenshots for employee_id={employee_id}")

    return {
        "items": [ScreenshotResponse.model_validate(row) for row in rows[:limit]],#  trim extra record
        "hasMore": has_more,
        "page": page,
        "limit": limit,
    }
