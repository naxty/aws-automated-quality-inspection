import json
import os
from urllib.parse import unquote_plus

import boto3

print("Loading function")

sqs_queue = os.environ.get("sqs_queue")
model_arn = os.environ.get("model_arn")


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    record = event["Records"][0]
    source_bucket = record["s3"]["bucket"]["name"]
    source_key = unquote_plus(record["s3"]["object"]["key"])

    print("Predict Picture")
    prediction_response = get_prediction(source_bucket, source_key)
    print("Prediction response:")
    print(prediction_response)

    print("Build SQS message")
    label, score = get_result_from_prediction_response(prediction_response)
    msg = {
        "bucket_name": source_bucket,
        "image_name": source_key,
        "prediction_label": label,
        "prediction_score": score,
    }
    print("Message: ", msg)

    print("Send msg to SQS")
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=sqs_queue)
    queue.send_message(MessageBody=json.dumps(msg))


def get_prediction(source_bucket, source_key):
    rekognition_client = boto3.client("rekognition")
    response = rekognition_client.detect_custom_labels(
        ProjectVersionArn=model_arn,
        Image={"S3Object": {"Bucket": source_bucket, "Name": source_key}},
    )
    return response


def get_result_from_prediction_response(prediction_response):
    result = prediction_response.get("CustomLabels")[0]
    label = result.get("Name")
    score = result.get("Confidence")

    new_label = "error"
    if label == "def_front":
        new_label = "defect"
    elif label == "ok_front":
        new_label = "okay"
    return new_label, score
