import json
import os

import boto3

print("Loading function")

target_bucket = os.environ.get("prediction_bucket")
prediction_threshold = float(os.environ.get("prediction_threshold"))


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    record = event["Records"][0]
    msg = json.loads(record.get("body").replace("'", '"'))
    print(msg)

    source_bucket = msg.get("bucket_name")
    image_name = msg.get("image_name")
    prediction_label = msg.get("prediction_label")
    prediction_score = msg.get("prediction_score")

    target_key = get_target_key(image_name, prediction_label, prediction_score)

    s3 = boto3.resource("s3")
    copy_source = {"Bucket": source_bucket, "Key": image_name}
    s3.meta.client.copy(copy_source, target_bucket, target_key)

    print(
        f"copied {image_name} from {source_bucket} in bucket {target_bucket} with key {target_key}"
    )


def get_target_key(image_name, prediction_label, prediction_score):
    target_key = prediction_label + "/" + image_name
    if prediction_score < prediction_threshold:
        target_key = "unclear" + "/" + image_name
    return target_key
