import pickle

import pika
from fastapi import FastAPI
from sqlalchemy.sql import insert
from starlette.status import HTTP_202_ACCEPTED

from db import database
from db.schema import Media, Status
from queues.rabbitmq import connection
from storage.s3 import generate_presigned_url

app = FastAPI()


@app.head("/")
def read_root():
    return None


@app.get("/generate-presigned-url")
def basic():
    try:
        url = generate_presigned_url("output", "1.mp4")
        return {"status": "success", "url": url}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/upload-webhook", status_code=HTTP_202_ACCEPTED)
def upload_webhook(event: dict):

    try:
        file_name = event["Records"][0]["s3"]["object"]["key"]

        file_size = event["Records"][0]["s3"]["object"]["size"]

        content_type = event["Records"][0]["s3"]["object"]["contentType"]

        print(f"file: {file_name}, size: {file_size}, content_type: {content_type}")

        client = database.get_db()

        db = next(client)

        insert_stmt = (
            insert(Media)
            .values(
                name=file_name,
                size=file_size,
                content_type=content_type,
                status=Status.PENDING,
            )
            .returning(Media.id)
        )
        result = db.execute(insert_stmt)

        row = result.fetchone()

        connection.channel().basic_publish(
            exchange="video_exchange",
            routing_key="video",
            body=pickle.dumps({"file_name": file_name, "id": row.id}),
            properties=pika.BasicProperties(content_type="application/octet-stream"),
        )

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
