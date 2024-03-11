import time
import boto3

sqs = boto3.client('sqs', region_name='us-east-1')
autoscaling = boto3.client('autoscaling', region_name='us-east-1')

max_seen_messages = 0
attempt = 0
max_attempts = 10

while True:
    time.sleep(8)

    resp = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=["app-tier-asg"], MaxRecords=1)
    instance_count = 0
    for instance in resp['AutoScalingGroups'][0]['Instances']:
        if instance['LifecycleState'] == 'InService':
            instance_count += 1

    resp = sqs.get_queue_attributes(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/471112779141/1229511168-req-queue",
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    queue_size = int(resp['Attributes']['ApproximateNumberOfMessages']) + int(resp['Attributes']['ApproximateNumberOfMessagesNotVisible'])

    print("Number of instances in service: ", instance_count)
    print("Queue length: ", queue_size)

    if instance_count < queue_size:
        new_instance_count = min(20, queue_size)
        if new_instance_count > max_seen_messages:
            max_seen_messages = new_instance_count
            print("New desired capacity: ", new_instance_count)
            autoscaling.set_desired_capacity(AutoScalingGroupName="app-tier-asg", DesiredCapacity=new_instance_count)
    elif instance_count > queue_size:
        if instance_count < max_seen_messages:
            attempt += 1
            if attempt == max_attempts:
                max_seen_messages = 0
                attempt = 0
                print("Could not fully scale up")
            else:
                print("More attempts left to scale up")
                continue
        max_seen_messages = 0
        attempt = 0
        new_instance_count = max(0, queue_size)
        print("New desired capacity: ", new_instance_count)
        autoscaling.set_desired_capacity(AutoScalingGroupName="app-tier-asg", DesiredCapacity=new_instance_count)