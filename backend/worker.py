from concurrent.futures import ThreadPoolExecutor
from functools import partial
import pickle

import ffmpeg
import pika
from botocore.httpsession import os
from faster_whisper import WhisperModel

from db import database
from db.schema import Base, Media, Status
from storage.s3 import download_media

executor = ThreadPoolExecutor(max_workers=5)

credentials = pika.PlainCredentials(username="rabbitmq", password="rabbitmq")
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="localhost", credentials=credentials)
)

channel = connection.channel()

client = database.get_db()

db = next(client)

dir = "outputs"

def voice_to_text(file_path: str):
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = whisper_model.transcribe(file_path, word_timestamps=True)
    return list(segments)


def export_video_with_subtitles(file_name: str, file_path: str, segments):
    os.makedirs(f"{dir}/{file_name}", 755, True)
    with open(f"{dir}/{file_name}/subtitles.srt", "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)

            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment.text.strip()}\n\n")
    source = ffmpeg.input(file_path)
    video = source.video.filter("subtitles", f"{dir}/{file_name}/subtitles.srt")
    ffmpeg.output(
        video,
        source.audio,
        f"{dir}/{file_name}/{file_name}.mp4",
        vcodec="libx264",
        pix_fmt="yuv420p",
        acodec="aac",
        movflags="+faststart",
    ).run(overwrite_output=True, capture_stderr=True)

    os.remove(f"{dir}/{file_name}/subtitles.srt")


def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def process_video(file_name: str):

    try:

        os.makedirs(dir, 755, True)

        bucket_name = "output"

        file_path = f"/tmp/{file_name}"

        print(f"file name: {file_name}")

        download_media(bucket_name, file_name, file_path)

        print("processing")

        stream = ffmpeg.input(file_path)

        audio = stream.audio

        output_audio = f"{dir}/{file_name}.m4a"

        output = ffmpeg.output(audio, output_audio, acodec="copy")

        print(f"output: {output}")

        ffmpeg.run(output, overwrite_output=True, capture_stderr=True)

        print("done")

        segments = voice_to_text(output_audio)
        export_video_with_subtitles(file_name, file_path, segments)

    except ffmpeg.Error as e:
        print(f"An error occurred: {e.stderr.decode() if e.stderr else e}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def ack_message(delivery_tag):
    channel.basic_ack(delivery_tag)


def process_message(ch, method, properties, body):

    headers = properties.headers or {}

    json_body = pickle.loads(body)
    file_name = json_body['file_name']
    id = json_body['id']


    delivery_tag = method.delivery_tag

    def worker():

        MAX_RETRIES = 3

        death_count = 0

        if 'x-death' in headers:
            for death in headers['x-death']:
                if death['queue'] == 'retry_queue':
                    death_count = death['count']
        try:
            process_video(file_name)

            connection.add_callback_threadsafe(partial(ack_message, delivery_tag))
            connection.add_callback_threadsafe(
                partial(channel.basic_ack, delivery_tag=delivery_tag)
            )
        except Exception as e:

            if death_count >= MAX_RETRIES:
                channel.basic_publish(exchange="dlx_exchange", routing_key="failed", body=body, properties=properties)
                connection.add_callback_threadsafe(
                    partial(channel.basic_ack, delivery_tag=delivery_tag)
                )

                media = db.get(Media, id)

                if media:
                    media.status = Status.FAILED
                    db.commit()
            else:
                connection.add_callback_threadsafe(
                    partial(channel.basic_nack, delivery_tag=delivery_tag, requeue=False)
                )
                print(f"Retry {death_count + 1}/{MAX_RETRIES}: {e}")

    executor.submit(worker)


channel.basic_qos(prefetch_count=5)

channel.basic_consume(
    queue="video_queue", on_message_callback=process_message, auto_ack=False
)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
