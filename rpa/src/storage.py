import os
import aioboto3
from botocore.config import Config

S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "cdcadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "cdcsecret")
S3_BUCKET = os.getenv("S3_BUCKET", "survey-images")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://s3:8333")

session = aioboto3.Session()

async def get_s3_client():
    return session.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(s3={'addressing_style': 'path'}), # Crucial for MinIO/SeaweedFS
        verify=False
    )

async def upload_image(file_content: bytes, file_name: str, content_type: str = "image/jpeg") -> str:
    """
    Upload image to SeaweedFS S3 and return the path.
    """
    async with await get_s3_client() as s3:
        # Create bucket if not exists (ignore error if exists)
        try:
            await s3.create_bucket(Bucket=S3_BUCKET)
        except:
            pass
            
        await s3.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        return f"{S3_BUCKET}/{file_name}"

async def delete_image(file_name: str):
    async with await get_s3_client() as s3:
        try:
            await s3.delete_object(Bucket=S3_BUCKET, Key=file_name)
        except:
            pass
