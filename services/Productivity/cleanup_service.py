# app/services/screenshot_cleanup.py

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core import config
from model.Productivity.screenshot import Screenshot
from utils.productivity.s3 import delete_from_s3
import logging

logger = logging.getLogger(__name__)


def delete_old_screenshots(db: Session) -> int:
    """
    Delete screenshots older than configured retention minutes
    and remove corresponding S3 objects.
    """

    cutoff = datetime.utcnow() - timedelta(
        minutes=config.S3_SCREENSHOT_RETENTION_MINUTES
    )

    old_screenshots = db.query(Screenshot).filter(
        Screenshot.timestamp < cutoff
    ).all()

    logger.info(
        f"Found {len(old_screenshots)} screenshots older than "
        f"{config.S3_SCREENSHOT_RETENTION_MINUTES} minute(s)"
    )

    deleted_count = 0

    for screenshot in old_screenshots:
        try:
            image_path = screenshot.image_path

            key = (
                image_path
                .replace(config.CLOUDFRONT_URL + "/", "")
                .replace(
                    f"https://{config.AWS_BUCKET_NAME}.s3."
                    f"{config.AWS_REGION}.amazonaws.com/",
                    ""
                )
            )

            logger.info(f"Trying to delete screenshot id={screenshot.id}")
            logger.info(f"S3 key = {key}")

            if delete_from_s3(key):
                db.delete(screenshot)
                deleted_count += 1
                logger.info(f"Deleted screenshot id={screenshot.id}")
            else:
                logger.error(
                    f"Failed S3 delete for screenshot id={screenshot.id}"
                )

        except Exception as e:
            logger.error(
                f"Error deleting screenshot id={screenshot.id}: {str(e)}"
            )

    if deleted_count > 0:
        db.commit()
        logger.info(
            f"Cleanup completed successfully. "
            f"Deleted {deleted_count} screenshots."
        )
    else:
        logger.info("No screenshots deleted.")

    return deleted_count
