from datetime import timedelta

from minio import Minio
from minio.error import S3Error


def get_storage_client() -> Minio:
    return Minio(
        "localhost:9000",
        access_key="admin",
        secret_key="supersecretpassword",
        secure=False,
    )


client = get_storage_client()


def create_bucket(bucket_name: str):
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print("Created bucket:", bucket_name)
        else:
            print("Bucket already exists")
    except S3Error as err:
        print("Error creating bucket:", err)


def generate_presigned_url(bucket_name: str, file_name: str):

    return client.presigned_put_object(bucket_name, file_name, timedelta(hours=1))

def download_media(bucket_name: str, file_name: str, output_path: str):
    client.fget_object(bucket_name, file_name, output_path)