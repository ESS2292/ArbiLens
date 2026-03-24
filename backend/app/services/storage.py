from http import HTTPStatus

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.errors import AppError


class ObjectStorageService:
    def __init__(self, client: BaseClient | None = None) -> None:
        self.settings = get_settings()
        self.client = client or boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region,
        )

    def upload_bytes(self, *, content: bytes, key: str, content_type: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                "Failed to store the uploaded file.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="storage_error",
            ) from exc
        return key

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.settings.s3_bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                "Failed to delete the uploaded file after an error.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="storage_cleanup_error",
            ) from exc

    def download_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.settings.s3_bucket, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                "Failed to read the stored file.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="storage_read_error",
            ) from exc

    def generate_download_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                "Failed to generate a report download URL.",
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="storage_presign_error",
            ) from exc


def get_s3_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def get_object_storage_service() -> ObjectStorageService:
    return ObjectStorageService(client=get_s3_client())
