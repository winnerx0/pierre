import pika

credentials = pika.PlainCredentials(username='rabbitmq', password='rabbitmq')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))

channel = connection.channel()

channel.queue_declare(queue='videos', durable=True)