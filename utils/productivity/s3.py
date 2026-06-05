import boto3
from botocore.exceptions import ClientError
from uuid import uuid4
from app.core import config



# S3 Client

s3_client = boto3.client(
    "s3",
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    region_name=config.AWS_REGION,
)

BUCKET_NAME = config.AWS_BUCKET_NAME
CLOUDFRONT_URL = config.CLOUDFRONT_URL



# Upload Function

from app.utils.logger import get_logger

logger = get_logger(__name__)

def upload_to_s3(file, folder: str = "screenshots") -> str:
    """Upload file to S3 and return CloudFront URL."""

    logger.info(f"Uploading file to S3: folder={folder}, filename={file.filename}")
    if not file.filename:
        logger.error("No filename provided for S3 upload")
        raise ValueError("No filename provided")

    # Get file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    filename = f"{uuid4()}.{ext}"

    key = f"{folder}/{filename}"

    # Reset file pointer (IMPORTANT)
    file.file.seek(0)

    try:
        s3_client.upload_fileobj(
            file.file,
            BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream",
            },
        )
        url = f"{CLOUDFRONT_URL}/{key}"
        logger.info(f"S3 upload successful: key={key}, url={url}")
        return url

    except ClientError as e:
        logger.error(f"S3 upload error: {e}", exc_info=True)
        raise



# Delete Function

def delete_from_s3(key: str) -> bool:
    """Delete object from S3 using key (e.g. 'screenshots/uuid.png')"""

    logger.info(f"Deleting from S3: key={key}")
    try:
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=key
        )
        logger.info(f"S3 delete successful: key={key}")
        return True

    except ClientError as e:
        logger.error(f"S3 delete error for key={key}: {e}", exc_info=True)
        return False
