import time
import boto3

sqs = boto3.client('sqs', region_name='us-east-1')
ec2 = boto3.client('ec2', region_name='us-east-1')

RECREATE_ATTEMPT = 15
MAX_ATTEMPTS = 25

def create_instance(name):
    resp = ec2.run_instances(
        LaunchTemplate={'LaunchTemplateName': 'app-tier-template'},
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': name}]
            }
        ]
    )
    return resp['Instances'][0]['InstanceId']

def verify_requested_instances(requested_capacity, instance_ids, instance_running, attempt):
    for i, instance_id in enumerate(instance_ids):
        if i < requested_capacity:
            if instance_id is None:
                instance_ids[i] = create_instance('app-tier-instance-' + str(i + 1))
            elif not instance_running[i] and attempt == RECREATE_ATTEMPT:
                print("Recreating instance: ", i + 1)
                ec2.terminate_instances(InstanceIds=[instance_id])
                instance_ids[i] = create_instance('app-tier-instance-' + str(i + 1))
        elif instance_id is not None:
                ec2.terminate_instances(InstanceIds=[instance_id])
                instance_ids[i] = None


def start_controller():
    requested_capacity = 0
    max_seen_messages = 0
    attempt = 0
    instance_ids = [None]*20
    instance_running = [False]*20

    while True:
        time.sleep(5)

        running_instance_ids = []
        for instance_id in instance_ids:
            if instance_id is not None:
                running_instance_ids.append(instance_id)

        instance_count = 0
        if len(running_instance_ids) > 0:
            resp = ec2.describe_instance_status(InstanceIds=running_instance_ids, IncludeAllInstances=True)
            for instance_status in resp['InstanceStatuses']:
                i = instance_ids.index(instance_status['InstanceId'])
                if instance_status['InstanceState']['Name'] == 'running':
                    instance_running[i] = True
                    instance_count += 1
                else:
                    instance_running[i] = False

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
                print("New requested capacity: ", new_instance_count)
                requested_capacity = new_instance_count
        elif instance_count > queue_size:
            if instance_count < max_seen_messages:
                attempt += 1
                if attempt == MAX_ATTEMPTS:
                    max_seen_messages = 0
                    attempt = 0
                    print("Could not fully scale up")
                else:
                    print("More attempts left to scale up")
                    verify_requested_instances(requested_capacity, instance_ids, instance_running, attempt)
                    continue
            max_seen_messages = 0
            attempt = 0
            new_instance_count = max(0, queue_size)
            print("New requested capacity: ", new_instance_count)
            requested_capacity = new_instance_count
        verify_requested_instances(requested_capacity, instance_ids, instance_running, attempt)

while True:
    try:
        ec2_resource = boto3.resource('ec2', 'us-east-1')
        old_instances = list(ec2_resource.instances.filter(Filters=[{'Name': 'tag:Name', 'Values': ["app-tier-instance*"]}]))
        if len(old_instances) > 0:
            ec2.terminate_instances(InstanceIds=[old_instance.id for old_instance in old_instances])
        start_controller()
    except Exception:
        print("Controller died, restarting")