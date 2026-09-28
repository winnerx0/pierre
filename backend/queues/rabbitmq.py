import pika

credentials = pika.PlainCredentials(username='rabbitmq', password='rabbitmq')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))

channel = connection.channel()

channel.exchange_declare(exchange="video_exchange", exchange_type="direct")
channel.exchange_declare(exchange="retry_exchange", exchange_type="direct")
channel.exchange_declare(exchange="dlx_exchange", exchange_type="direct")

channel.queue_declare(queue="video_queue", durable=True, arguments={
    "x-dead-letter-exchange": "retry_exchange",
    "x-dead-letter-routing-key": "retry"
})

channel.queue_declare(queue="retry_queue", durable=True, arguments={
    'x-message-ttl': 5000,
    "x-dead-letter-exchange": "video_exchange",
    "x-dead-letter-routing-key": "video"
})

channel.queue_declare(queue="dlx_queue", durable=True)

channel.queue_bind(queue='video_queue', exchange="video_exchange", routing_key="video")
channel.queue_bind(queue='retry_queue', exchange="retry_exchange", routing_key="retry")
channel.queue_bind(queue='dlx_queue', exchange="dlx_exchange", routing_key="failed")