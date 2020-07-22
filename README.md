# Amazon Web Service Automated Quality Inspection
![Architecture](docs/aws_highlevelarchitektur_overview.png)

This repository is a showcase about how to leverage Amazon Web Services (aws) to train and deploy a machine learning project without any deep knowledge about machine learning frameworks. 
 The underlying use case is automated detection of defect components in manufacturing. For this purpose we upload pictures of the components to aws. Then, we classify the image using a machine learning model. Images that are not classified with sufficient certainty by the model can be manually postprocessed using a simple user interface.

We utilizing different services such as [S3](https://aws.amazon.com/s3/), [Rekognition](https://aws.amazon.com/rekognition/), [Lambda Functions](https://aws.amazon.com/lambda/), [Simple Queue Service](https://aws.amazon.com/sqs/) and [Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) to implement the machine learning system. The Rekognition image classification model is trained on the [product image data for quality insepection](https://www.kaggle.com/ravirajsinh45/real-life-industrial-dataset-of-casting-product).

## Prerequirements
You need access to AWS. For this tutorial, we used a AWS Account with `AdministratorAccess` for simplicity. In a real production environment, we would satisfy the principle of least privilege and restrict the account appropriately.

In addition, we use the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html). We assume that the following environment variables are set
```
export AWS_ACCESS_KEY_ID=<<my-admin-account-access-key-id>>
export AWS_SECRET_ACCESS_KEY=<<my-admin-account-secret-access-key>>
export AWS_DEFAULT_REGION=eu-west-1 
```
or that the cli commands are issued with a suitable aws-profile.

## Amazon Rekognition

Before we can train the Rekognition model we need to upload the data to S3. Because custom labels for Rekognition are only available in the Ireland region (eu-west-1) we create a bucket in this region. Here, we require the environment variables.
```sh
TRAINING_DATA_BUCKET="product-quality-data"
``` 
Bucket names in AWS are unique, therefore you probably need to change it.

1. Download the [dataset](https://www.kaggle.com/ravirajsinh45/real-life-industrial-dataset-of-casting-product) and put it inside the [data](data/)-folder. Extract the zip file.
```
data
└── casting_data
    ├── test
    │   ├── def_front
    │   │   ├── ....
    │   │   └── new__0_9334.jpeg
    │   └── ok_front
    │       ├── ....
    │       └── cast_ok_0_9996.jpeg
    └── train
        ├── def_front
        │   ├── ...
        │   └── cast_def_0_9997.jpeg
        └── ok_front
            ├── ...
            └── cast_ok_0_9998.jpeg
```

2. Create a S3 bucket and upload the data:
```sh
aws s3 mb s3://${TRAINING_DATA_BUCKET}
aws s3 cp data/casting_data s3://${TRAINING_DATA_BUCKET}/ --recursive
```

3. First time setup -> rekognition create S3 bucket -> In our case: 
custom-labels-console-eu-west-1-5c5621d943
![AWS Rekognition first time set up](docs/aws_rekognition_first_time_set_up.png)
4. Create a project -> contains all the "management" details about images, labels and models
![AWS Rekognition create project](docs/aws_rekognition_create_project.png)
5. Create the datasets -> Automatically add labels based on folder names
Import the images from the S3 Bucket
![AWS Rekognition create dataset](docs/aws_rekognition_create_dataset_from_bucket.png)
We can inspect the dataset within the AWS Rekognition UI.
![AWS Rekognition inspect data](docs/aws_rekognition_dataset_inspection.png)
We will do the same with the test dataset and provide the S3 folder location as `S3://${TRAINING_DATA_BUCKET}/casting_data/test`.
Finally the project overview should look like the following:
![AWS Rekognition inspect data](docs/aws_rekognition_project_overview.png)
6. Start the training:
![AWS Rekognition train model](docs/aws_rekognition_train_model.png)
Downsides:
- Not possible to select time of training. Explain costs here
TODO: is there a notification after the training has finished?

## Run Rekognition Server
Cost model
1. Start model
```
aws rekognition start-project-version --project-version-arn "arn:aws:rekognition:eu-west-1:452161433274:project/product_quality/version/product_quality.2020-07-17T09.39.14/1594971554815" --min-inference-units 1 --region eu-west-1
```
2. Test via console:
```
aws rekognition detect-custom-labels \
  --project-version-arn "arn:aws:rekognition:eu-west-1:452161433274:project/product_quality/version/product_quality.2020-07-17T09.39.14/1594971554815" \
  --image '{"S3Object": {"Bucket": "custom-labels-console-eu-west-1-5c5621d943","Name": "assets/casting_data/test/ok_front/cast_ok_0_10.jpeg"}}' \
  --region eu-west-1
```
3. Stop model


## Lambda Integration

![Lambda_functions_highlevel](docs/aws_highlevelarchitektur_lambdafunctions.png)

For our setup, we require two lambda functions. The first function classifies new images via the Rekognition model and publishes the prediction result to SQS. The second function takes the prediction results and distributes the inbound pictures accordingly.

#### Preliminaries

Before we can deploy the lambda functions, we have to create a executioner role with adequate permissions. In a real production environment, we should satisfy the principle of least privilege. In this demo, however, we keep it simple and create one role for both functions.

First, we create the executioner role via

```
aws iam create-role --role-name lambda-ex --assume-role-policy-document '{"Version": "2012-10-17","Statement": [{ "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'
```
Then, we add the policies `AWSLambdaFullAccess`, `AmazonSQSFullAccess` and `AmazonRekognitionCustomLabelsFullAccess` with

```
aws iam attach-role-policy --role-name lambda-ex --policy-arn arn:aws:iam::aws:policy/AWSLambdaFullAccess

aws iam attach-role-policy --role-name lambda-ex --policy-arn arn:aws:iam::aws:policy/AmazonSQSFullAccess

aws iam attach-role-policy --role-name lambda-ex --policy-arn arn:aws:iam::aws:policy/AmazonRekognitionCustomLabelsFullAccess
```
In the following, we attach this role to both lambda functions.

#### Prediction

The [predict](lambda_functions/predict/predict.py) function triggers for each picture that is uploaded to the inbound bucket. It sends the picture to the custom Rekognition model in order to obtain a prediction. The result of this classification is published to a SQS queue. We publish messages of the form.
```
msg = {
    "bucket_name": ,
    "image_name": ,
    "prediction_label": ,
    "prediction_score": ,
}
```
In order to deploy the function we require the environment variables
```
ACCOUNT_ID="<<my-account-id>>"
MODEL_ARN="<<my-rekognition-mode-arn"
INBOUND_BUCKET="<<my_prediction_bucket>>"
PREDICTION_QUEUE="<<my_prediction_queue>>"
PREDICT_LAMBDA_NAME="predict_picture"
```
Here, the `ACCOUNT_ID` is the ID of the aws account. The `MODEL_ARN` is the ARN of the custom Rekognition model of the previous step which can be found in the Rekognition UI. Whereas the names for the bucket `INBOUND_BUCKET` and SQS queue name `PREDICTION_QUEUE` can be chosen freely. The value for `PREDICT_LAMBDA_NAME` doesn't have to be changed.

We create the bucket and the SQS queue with
```
aws s3 mb s3://${INBOUND_BUCKET}
```
and
```
SQS_QUEUE_URL=$(aws sqs create-queue --queue-name ${PREDICTION_QUEUE} --query "QueueUrl")
```
Here, we store the `SQS_QUEUE_URL` for later. Then, we zip the code for the lambda function with
```
cd lambda_functions/predict
zip predict_function.zip predict.py
cd ../..
```
and finally deploy the lambda using
```
aws lambda create-function \
--function-name ${PREDICT_LAMBDA_NAME} \
--zip-file fileb://lambda_functions/predict/predict_function.zip \
--runtime python3.7 \
--role arn:aws:iam::452161433274:role/lambda-ex \
--handler predict.lambda_handler \
--environment Variables="{model_arn=${MODEL_ARN},sqs_queue=${PREDICTION_QUEUE}}"
```
Next, we have to give permission to the inbound bucket to trigger the lambda function
```
aws lambda add-permission \
--function-name ${PREDICT_LAMBDA_NAME} \
--action lambda:InvokeFunction \
--statement-id s3invoke \
--principal s3.amazonaws.com \
--source-arn arn:aws:s3:::${INBOUND_BUCKET} \
--source-account ${ACCOUNT_ID}
```
Then, we can add the event notification to the bucket
```
aws s3api put-bucket-notification-configuration \
 --bucket ${INBOUND_BUCKET} \
 --notification-configuration file://lambda_functions/s3triggerNotification.json
```
using [s3triggerNotification.json](lambda_functions/s3triggerNotification.json) with the correct arn for the lambda function.

#### Moving

![Lambda_functions_moving](docs/aws_lambda_functions_moving.png)

The [moving](lambda_functions/move/move.py) function triggers for new events on the SQS queue `PREDICTION_QUEUE`. The function moves the picture into the respective subfolder in the prediction bucket and deletes it from the inbound bucket. Here, we explicitly check if the prediction score is above a given threshold. We move images with low score into a special folder for manual postprocessing because we only trust predictions with a high score for automated processing. The resulting folder structure looks as follows.   
```
prediction_bucket
├── ok
│   └── new_pic_4566.jpeg
│   └── new_pic_2353.jpeg
│   └── ...
├── defect
│   └── new_pic_3546.jpeg
│   └── new_pic_2453.jpeg
│   └── ...
└── unclear
    └── new_pic_1452.jpeg
    └── new_pic_1245.jpeg
    └── ...
```

We require the following environment variables for deploying the function.
```
PREDICTION_BUCKET="<<my_prediction_bucket>"
PREDICTION_THRESHOLD="0.8"

MOVE_LAMBDA_NAME="move_picture"
```
Here, the name for the bucket `PREDICTION_BUCKET` can be chosen freely. The `PREDICTION_THRESHOLD` defines the threshold for predictions that we consider unclear. Again, the value for `MOVE_CF_NAME` doesn't have to be changed.

We create the prediction bucket with
```
aws s3 mb s3://${PREDICTION_BUCKET}
```
Then we zip the function code and deploy the function with
```
cd lambda_functions/move
zip move_function.zip move.py
cd ../..

aws lambda create-function \
--function-name ${MOVE_LAMBDA_NAME} \
--zip-file fileb://lambda_functions/move/move_function.zip \
--runtime python3.7 \
--role arn:aws:iam::452161433274:role/lambda-ex \
--handler move.lambda_handler \
--environment Variables="{prediction_bucket=${PREDICTION_BUCKET}, prediction_threshold=${PREDICTION_THRESHOLD}}"
```
Next, we have to create an event source mapping between the SQS queue and the function
```
SQS_QUEUE_ARN=$(aws sqs get-queue-attributes --queue-url ${SQS_QUEUE_URL//\"} --attribute-names All --query Attributes.QueueArn)

aws lambda create-event-source-mapping \
 --function-name ${MOVE_LAMBDA_NAME} \
 --batch-size 1 \
 --event-source-arn ${SQS_QUEUE_ARN//\"}
```
Here, we use the `SQS_QUEUE_URL` from above.

## Elastic Beanstalk

![Elastic Beanstalk Architecture](docs/aws_highlevelarchitektur_frontend.png)

We serve an web application that can be used for reviewing images in the `unclear` folder, i.e., that have been classified by the model with a score below the chosen threshold. 

The server is written in Python using the [fastapi](https://fastapi.tiangolo.com/) framework. Through the server we serve a static page that is using React to display an image and as an user we can decide if the image is `defect` or `ok`. On the server side we retrieve the image from the `PREDICTION_BUCKET` and generate a pre-signed url that can be loaded directly from React. The server is deployed with Elastic Beanstalk. 

##### Preliminaries

In order to deploy the application with Elastic Beanstalk, we require the [EB CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html).

## Deployment on Elastic Beanstalk


First, change into the [ebs_app folder](ebs_app/) ane initialize the app deployment with
```
eb init product-quality-api --platform python-3.7  --region eu-west-1  
```
Among other things, this will create the folder `.elasticbeanstalk` containing a `config.yml` file. Then, we create the environment for our application using
```
eb create product-quality-api-env --single
```
The `--single` flag creates the environment with a single EC2 instance and without load balancer. Hence, this environment should only be used for testing.
This will take a while to complete. Finally, we can deploy the application into the environment with
```
eb deploy product-quality-api-env  
```
As soon as the deployment is complete, we can open the app in the browser via
```
eb open
```
The application shows images contained in the `unclear` folder in the `PREDICTION_BUCKET` and asks for a manual classification. In order to test the application you can simply upload some pictures into the folder. 
