"""MinIO / S3-compatible storage service."""

from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings


class StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )
        self._settings = settings

    def upload_file(
        self,
        bucket: str,
        key: str,
        file_obj: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file-like object. Returns the storage key."""
        self._ensure_bucket(bucket)
        self._client.upload_fileobj(
            file_obj,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def download_bytes(self, bucket: str, key: str) -> bytes:
        """Read a whole object into memory (report visuals are small PNGs)."""
        resp = self._client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()

    def get_presigned_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL valid for `expires_in` seconds."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete_object(self, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    def object_exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise

    def _ensure_bucket(self, bucket: str) -> None:
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError:
            self._client.create_bucket(Bucket=bucket)


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService()
