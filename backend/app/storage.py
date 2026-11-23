"""All object bytes encrypted before reaching the filesystem or MinIO."""

import os
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path(os.getenv("DATA_DIR", "data"))
ROOT.mkdir(parents=True, exist_ok=True)


def cipher():
    key = os.getenv("FORMFLOW_KEY")
    if not key:
        path = ROOT / "encryption.key"
        if not path.exists():
            path.write_bytes(Fernet.generate_key())
        key = path.read_bytes()
    return Fernet(key)


def client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
    )


def put(key, content):
    encrypted = cipher().encrypt(content)
    if os.getenv("MINIO_ENDPOINT"):
        c = client()
        try:
            c.head_bucket(Bucket="documents")
        except Exception:
            c.create_bucket(Bucket="documents")
        c.put_object(Bucket="documents", Key=key, Body=encrypted, ContentType="application/octet-stream")
    else:
        (ROOT / (key + ".enc")).write_bytes(encrypted)


def get(key):
    content = (
        client().get_object(Bucket="documents", Key=key)["Body"].read()
        if os.getenv("MINIO_ENDPOINT")
        else (ROOT / (key + ".enc")).read_bytes()
    )
    return cipher().decrypt(content)


def delete(key):
    if os.getenv("MINIO_ENDPOINT"):
        client().delete_object(Bucket="documents", Key=key)
    else:
        (ROOT / (key + ".enc")).unlink(missing_ok=True)
