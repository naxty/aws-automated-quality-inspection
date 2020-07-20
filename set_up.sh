#!/usr/bin/env bash

set -a
. ./config
set +a

## Create bucket inbound bucket
echo "create bucket $INBOUND_BUCKET"
aws s3 mb s3://${INBOUND_BUCKET}

## Create bucket prediction bucket
echo "create bucket $PREDICTION_BUCKET"
aws s3 mb s3://${PREDICTION_BUCKET}

## Create SQS Queue store QUEUE_URL to create create-event-source-mapping later
echo "create sqs queue $PREDICTION_QUEUE"
SQS_QUEUE_URL=$(aws sqs create-queue --queue-name ${PREDICTION_QUEUE} --query "QueueUrl")

### prediction function
## zip lambda_code
cd lambda_functions/predict
zip predict_function.zip predict.py
cd ../..

## Deploy cloud function (requires iam:arn from executioner role)
aws lambda create-function \
--function-name ${PREDICT_LAMBDA_NAME} \
--zip-file fileb://lambda_functions/predict/predict_function.zip \
--runtime python3.7 \
--role arn:aws:iam::452161433274:role/lambda-ex \
--handler predict.lambda_handler \
--environment Variables="{model_arn=${MODEL_ARN},sqs_queue=${PREDICTION_QUEUE}}"

## allow bucket to call function
aws lambda add-permission \
--function-name ${PREDICT_LAMBDA_NAME} \
--action lambda:InvokeFunction \
--statement-id s3invoke \
--principal s3.amazonaws.com \
--source-arn arn:aws:s3:::${INBOUND_BUCKET} \
--source-account ${ACCOUNT_ID}

## add bucket event notification (requires lambda:arn in json file)
aws s3api put-bucket-notification-configuration \
 --bucket ${INBOUND_BUCKET} \
 --notification-configuration file://lambda_functions/s3triggerNotification.json


### moving function
## zip
cd lambda_functions/move
zip move_function.zip move.py
cd ../..

## Deploy cloud function (requires iam:arn from executioner role)
aws lambda create-function \
--function-name ${MOVE_LAMBDA_NAME} \
--zip-file fileb://lambda_functions/move/move_function.zip \
--runtime python3.7 \
--role arn:aws:iam::452161433274:role/lambda-ex \
--handler move.lambda_handler \
--environment Variables="{prediction_bucket=${PREDICTION_BUCKET}, prediction_threshold=${PREDICTION_THRESHOLD}}"

## create mapping between sqs queue and lambda function
SQS_QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url ${SQS_QUEUE_URL//\"} --attribute-names All --query Attributes.QueueArn)

aws lambda create-event-source-mapping \
 --function-name ${MOVE_LAMBDA_NAME} \
 --batch-size 1 \
 --event-source-arn ${SQS_QUEUE_ARN//\"}

## start rekognition model (takes quite some time to complete)
aws rekognition start-project-version \
  --project-version-arn ${MODEL_ARN} \
  --min-inference-units 1