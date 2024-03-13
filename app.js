const express = require('express')
const app = express()
const port = 8000

const clientS3 = require('@aws-sdk/client-s3');
const clientSQS = require('@aws-sdk/client-sqs');

const s3Client = new clientS3.S3Client({ region: 'us-east-1' });
const sqsClient = new clientSQS.SQSClient({ region: 'us-east-1' });

const fileUpload = require('express-fileupload');
app.use(fileUpload());

app.get('/', (req, res) => {
    res.send('Web-tier server is running!')
})

app.post('/', async (req, res) => {
    const fname = req.files['inputFile'].name;
    const iname = fname.split('.').slice(0, -1).join('.');
    await s3Client.send(
        new clientS3.PutObjectCommand({
            Bucket: '1229511168-in-bucket',
            Key: fname,
            Body: req.files['inputFile'].data,
        })
    );
    await sqsClient.send(
        new clientSQS.SendMessageCommand({
            QueueUrl: 'https://sqs.us-east-1.amazonaws.com/471112779141/1229511168-req-queue',
            MessageBody: fname,
        })
    );
    await new Promise(resolve => setTimeout(resolve, 45000));
    for(let i = 0; i < 600; i++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const resp = await sqsClient.send(
            new clientSQS.ReceiveMessageCommand({
                QueueUrl: 'https://sqs.us-east-1.amazonaws.com/471112779141/1229511168-resp-queue',
                MaxNumberOfMessages: 10,
                VisibilityTimeout: 0,
                WaitTimeSeconds: 5,
            })
        );
        if (!resp.Messages) {
            continue;
        }
        for (let j = resp.Messages.length - 1; j >= 0; --j) {
            let message = resp.Messages[j]
            if (message.Body.startsWith(iname)) {
                await sqsClient.send(
                    new clientSQS.DeleteMessageCommand({
                        QueueUrl: 'https://sqs.us-east-1.amazonaws.com/471112779141/1229511168-resp-queue',
                        ReceiptHandle: message.ReceiptHandle,
                    })
                );
                res.send(message.Body);
                return;
            }
        }
    }
})

app.listen(port, () => {
    console.log(`Web tier listening on port ${port}`)
})