import boto3
from botocore.client import Config


def get_storage_client():
    return boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="admin",
        aws_secret_access_key="password",
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


client = get_storage_client()


def create_bucket(bucket_name: str):
    try:
        client.create_bucket(Bucket=bucket_name)
        print("Created bucket:", bucket_name)
    except client.exceptions.BucketAlreadyOwnedByYou as err:
        print("Error creating bucket:", err)


def generate_presigned_url(bucket_name: str, file_name: str):

    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket_name, "Key": file_name},
        ExpiresIn=3600,
    )


def download_media(bucket_name: str, file_name: str, output_path: str):
    client.download_file(bucket_name, file_name, output_path)
