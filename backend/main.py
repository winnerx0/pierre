from fastapi import FastAPI

from db import database
from db.schema import Media, Status
from rabbitmq import connection
from storage.minio import generate_presigned_url

app = FastAPI()


@app.get("/generate-presigned-url")
def basic():
    try:
        url = generate_presigned_url("output", "1.mp4")
        return {"status": "success", "url": url}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/upload-webhook")
def upload_webhook(event: dict):

    try:
        file_name = event["Records"][0]["s3"]["object"]["key"]

        print(f"file: {file_name}")

        client = database.get_db()

        db = next(client)

        db.add(Media(name=file_name, status=Status.PENDING))
        db.commit()

        connection.channel().basic_publish(
            exchange="", routing_key="videos", body=file_name
        )

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
