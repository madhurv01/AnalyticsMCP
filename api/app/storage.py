import boto3
from botocore.client import Config

from app.config import settings

_session = boto3.session.Session()


def _client(endpoint: str):
    return _session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    _client(settings.s3_endpoint_url).put_object(
        Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
    )


def get_bytes(key: str) -> bytes:
    obj = _client(settings.s3_endpoint_url).get_object(Bucket=settings.s3_bucket, Key=key)
    return obj["Body"].read()


def delete_key(key: str) -> None:
    _client(settings.s3_endpoint_url).delete_object(Bucket=settings.s3_bucket, Key=key)


def presigned_get(key: str, filename: str, ttl: int = 300) -> str:
    # sign against the browser-reachable endpoint
    return _client(settings.s3_public_endpoint_url).generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=ttl,
    )
