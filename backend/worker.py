from concurrent.futures import ThreadPoolExecutor
from functools import partial

import ffmpeg
from faster_whisper import WhisperModel
from minio.error import S3Error

from rabbitmq import channel, connection
from storage.minio import client

executor = ThreadPoolExecutor(max_workers=5)


def download_video(bucket_name: str, object_name: str, file_path: str):

    print("downloading in progress...")

    client.fget_object(bucket_name, object_name, file_path)


def voice_to_text(file_path: str):
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = whisper_model.transcribe(file_path, word_timestamps=True)
    return list(segments)

def export_video_with_subtitles(file_path: str, segments):
    with open("subtitles.srt", "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
    
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment.text.strip()}\n\n")
    source = ffmpeg.input(file_path)
    video = source.video.filter("subtitles", "subtitles.srt")
    ffmpeg.output(
        video,
        source.audio,
        "output.mp4",
        vcodec="libx264",
        pix_fmt="yuv420p",
        acodec="aac",
        movflags="+faststart",
    ).run(overwrite_output=True, capture_stderr=True)
            
def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def process_video(file_name: str):

    try:

        bucket_name = "output"

        file_path = f"/tmp/{file_name}"

        print(f"file name: {file_name}")

        download_video(bucket_name, file_name, file_path)

        print("processing")

        stream = ffmpeg.input(file_path)

        print(f"stream: {stream}")

        audio = stream.audio

        output_audio = f"./{file_name}.m4a"

        output = ffmpeg.output(audio, output_audio, acodec="copy")

        print(f"output: {output}")

        ffmpeg.run(output, overwrite_output=True, capture_stderr=True)

        print("done")

        segments = voice_to_text(output_audio)
        export_video_with_subtitles(file_path, segments)

    except ffmpeg.Error as e:
        print(f"An error occurred: {e.stderr.decode() if e.stderr else e}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def ack_message(delivery_tag):
    channel.basic_ack(delivery_tag)


def process_message(ch, method, properties, body):

    file_name = body.decode()

    delivery_tag = method.delivery_tag

    def worker():
        try:
            process_video(file_name)

            connection.add_callback_threadsafe(partial(ack_message, delivery_tag))
        except Exception as e:
            print(f"An error occurred: {e}")
            connection.add_callback_threadsafe(
                partial(channel.basic_nack, delivery_tag=delivery_tag, requeue=False)
            )

    executor.submit(worker)


channel.basic_qos(prefetch_count=5)

channel.basic_consume(
    queue="videos", on_message_callback=process_message, auto_ack=False
)

print(" [*] Waiting for messages. To exit press CTRL+C")
channel.start_consuming()
