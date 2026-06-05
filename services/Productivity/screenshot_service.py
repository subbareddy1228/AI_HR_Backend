from sqlalchemy.orm import Session
from model.Productivity.screenshot import Screenshot
from utils.productivity.helpers import save_file
from utils.productivity.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

def save_screenshot(db: Session, employee_id: int, file):
    logger.info(f"Saving screenshot for employee_id={employee_id}")
    try:
        file_url = save_file(file, "screenshots")
        logger.debug(f"File saved to: {file_url}")

        screenshot = Screenshot(
            employee_id=employee_id,
            image_path=file_url,
            timestamp=datetime.utcnow()
        )

        db.add(screenshot)
        db.commit()
        db.refresh(screenshot)
        logger.info(f"Screenshot saved successfully: id={screenshot.id}")
        return screenshot
    except Exception as e:
        logger.error(f"Error saving screenshot for employee_id={employee_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise
