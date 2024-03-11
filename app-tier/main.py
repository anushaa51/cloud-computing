import time
import os
import boto3
import subprocess

sqs = boto3.resource('sqs',region_name='us-east-1')
req_queue = sqs.get_queue_by_name(QueueName="1229511168-req-queue")
resp_queue = sqs.get_queue_by_name(QueueName="1229511168-resp-queue")

s3 = boto3.resource('s3',region_name='us-east-1')
in_bucket = s3.Bucket('1229511168-in-bucket')
out_bucket = s3.Bucket('1229511168-out-bucket')

prev_no_messages = False

while True:
    if prev_no_messages:
        prev_no_messages = False
        time.sleep(5)
    time.sleep(1)
    messages = req_queue.receive_messages(MaxNumberOfMessages=3, VisibilityTimeout=5, WaitTimeSeconds=5)
    if not messages:
        prev_no_messages = True
        continue
    for message in messages:
        image_key = message.body
        image = image_key.split('.')[0]
        in_bucket.download_file(image_key, image_key)
        classification = subprocess.run(['python3', 'face_recognition.py', image_key], stdout=subprocess.PIPE).stdout.decode('utf-8')
        with open(image, "w") as f:
            f.write(classification)
        out_bucket.upload_file(image, image)
        if os.path.exists(image_key):
            os.remove(image_key)
        if os.path.exists(image):
            os.remove(image)
        resp_queue.send_message(MessageBody=f'{image}:{classification}')
        message.delete()