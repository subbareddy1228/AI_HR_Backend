from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core import config
from model.Productivity.screenshot import Screenshot
from utils.productivity.s3 import delete_from_s3
import logging

logger = logging.getLogger(__name__)


def delete_old_screenshots(db: Session) -> int:
    cutoff = datetime.utcnow() - timedelta(
        minutes=config.S3_SCREENSHOT_RETENTION_MINUTES
    )

    old_screenshots = db.query(Screenshot).filter(
        Screenshot.timestamp < cutoff
    ).all()

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

            if delete_from_s3(key):
                db.delete(screenshot)
                deleted_count += 1

        except Exception as e:
            logger.error(str(e))

    if deleted_count > 0:
        db.commit()

    return deleted_count
