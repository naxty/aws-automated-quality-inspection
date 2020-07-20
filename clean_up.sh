#!/usr/bin/env bash

set -a
. ./config
set +a

## Delete all objects and buckets
aws s3 rb s3://${INBOUND_BUCKET} --force
aws s3 rb s3://${PREDICTION_BUCKET} --force

## Delete SQS QUEUE
SQS_QUEUE_URL=$(aws sqs get-queue-url --queue-name ${PREDICTION_QUEUE} --query "QueueUrl")
aws sqs delete-queue --queue-url ${SQS_QUEUE_URL//\"}

## Delete lambda functions
aws lambda delete-function --function-name ${PREDICT_LAMBDA_NAME}
aws lambda delete-function --function-name ${MOVE_LAMBDA_NAME}

## Delete event source mapping
EVENT_SOURCE_UUID=$(aws lambda list-event-source-mappings --function-name ${MOVE_LAMBDA_NAME} --query "EventSourceMappings[0].UUID")
aws lambda delete-event-source-mapping --uuid ${EVENT_SOURCE_UUID//\"}

## Stop Rekognition model
aws rekognition stop-project-version --project-version-arn ${MODEL_ARN}