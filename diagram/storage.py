import os
import io
from minio import Minio
from minio.error import S3Error

MINIO_URL = os.getenv("MINIO_URL", "localhost:9000").split("http://")[-1] # Remove http:// if present
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET_NAME = "uml-diagrams" # Define a bucket name

# Initialize MinIO client
try:
    minio_client = Minio(
        MINIO_URL,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False # Set to True if using HTTPS
    )
except Exception as e:
    print(f"Error initializing MinIO client: {e}")
    minio_client = None

async def ensure_bucket_exists():
    if not minio_client:
        print("MinIO client not initialized. Cannot ensure bucket exists.")
        return
    try:
        found = minio_client.bucket_exists(MINIO_BUCKET_NAME)
        if not found:
            minio_client.make_bucket(MINIO_BUCKET_NAME)
            print(f"Bucket '{MINIO_BUCKET_NAME}' created.")
        else:
            print(f"Bucket '{MINIO_BUCKET_NAME}' already exists.")
    except S3Error as e:
        print(f"Error checking or creating bucket: {e}")
    except Exception as e: # Catch generic exceptions during client usage
        print(f"A general error occurred with MinIO client during bucket check: {e}")


async def upload_diagram_payload(object_name: str, data: bytes) -> str:
    if not minio_client:
        raise ConnectionError("MinIO client not initialized.")
    try:
        minio_client.put_object(
            MINIO_BUCKET_NAME,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type='application/json' # Assuming payload is JSON
        )
        # Construct the URL. This might need adjustment based on how MinIO is exposed.
        # If MinIO is behind a reverse proxy or has a specific public URL, use that.
        # For now, assuming direct access via MINIO_URL.
        return f"s3://{MINIO_BUCKET_NAME}/{object_name}" # Standard S3-like URI
        # Or: return f"http://{MINIO_URL}/{MINIO_BUCKET_NAME}/{object_name}" # HTTP URL
    except S3Error as e:
        print(f"Error uploading to MinIO: {e}")
        raise
    except Exception as e:
        print(f"A general error occurred during MinIO upload: {e}")
        raise

async def get_diagram_payload(object_name: str) -> bytes:
    if not minio_client:
        raise ConnectionError("MinIO client not initialized.")
    try:
        response = minio_client.get_object(MINIO_BUCKET_NAME, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        print(f"Error getting object from MinIO: {e}")
        if e.code == "NoSuchKey":
            raise FileNotFoundError(f"Diagram payload not found in MinIO: {object_name}")
        raise
    except Exception as e:
        print(f"A general error occurred during MinIO get: {e}")
        raise

async def delete_diagram_payload(object_name: str):
    if not minio_client:
        raise ConnectionError("MinIO client not initialized.")
    try:
        minio_client.remove_object(MINIO_BUCKET_NAME, object_name)
        print(f"Object '{object_name}' deleted from bucket '{MINIO_BUCKET_NAME}'.")
    except S3Error as e:
        print(f"Error deleting object from MinIO: {e}")
        raise
    except Exception as e:
        print(f"A general error occurred during MinIO delete: {e}")
        raise
