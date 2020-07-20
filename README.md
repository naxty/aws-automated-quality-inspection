# Amazon Web Service Automated Quality Inspection
![Architecture](docs/aws_highlevelarchitektur_overview.png)

This repository is a showcase about how to leverage Amazon Web Services (aws) to train and deploy a machine learning project without any deep knowledge about machine learning frameworks. 
 The underlying use case is automated detection of defect components in manufacturing. For this purpose we upload pictures of the components to aws. Then, we classify the image using a machine learning model. Images that are not classified with sufficient certainty by the model can be manually postprocessed using a simple user interface.

We utilizing different services such as [S3](https://aws.amazon.com/s3/), [Rekognition](https://aws.amazon.com/rekognition/), [Lambda Functions](https://aws.amazon.com/lambda/), [Simple Queue Service](https://aws.amazon.com/sqs/) and [Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) to implement the machine learning system. The Rekognition image classification model is trained on the [product image data for quality insepection](https://www.kaggle.com/ravirajsinh45/real-life-industrial-dataset-of-casting-product).

## Amazon Rekognition

Using Amazon Rekognition Custom Labels.

Custom labels available in the Ireland region (eu-west-1).

1. First time setup -> rekognition create S3 bucket -> In our case: 
custom-labels-console-eu-west-1-5c5621d943
![AWS Rekognition first time set up](docs/aws_rekognition_first_time_set_up.png)
1. Create a project -> contains all the "management" details about images, labels and models
![AWS Rekognition create project](docs/aws_rekognition_create_project.png)
1. Create a dataset -> Automatically add labels based on folder names
[] Command to upload images to S3 via CLI
[] Otherwise drop and drop "casting_data" from the data folder into the S3 Bucket via AWS console.
Import the images from Amazaon S3 Bucket
![AWS Rekognition create dataset](docs/aws_rekognition_dataset_create.png)
![AWS Rekognition select data](docs/aws_rekognition_dataset_select.png)
We can inspect the dataset within the AWS Rekognition UI.
![AWS Rekognition inspect data](docs/aws_rekognition_dataset_inspection.png)
We will do the same with the test dataset and provide the S3 folder location as S3://$BUCKET/assets/casting_data/train
Finally the project overview should look like the following:
![AWS Rekognition inspect data](docs/aws_rekognition_project_overview.png)
Start the training:
![AWS Rekognition train model](docs/aws_rekognition_train_model.png)
Downsides:
- Not possible to select time of training. Explain costs here
TODO: is there a notification after the training has finished?

Trainings results are impressive

## Run Rekognition Server
Cost model
1. Prerequisites:
    - setup IAM account `IAM` -> `Users` -> `Add user`
    - Add `AmazonRekognitionCustomLabelsFullAccess`-Role
    - Download csv file with credentials and setup the profile
1. Setup awscli locally `aws configure --profile product_quality`
1. `EXPORT AWS_PROFILE=product_quality`
1. 
aws rekognition start-project-version --project-version-arn "arn:aws:rekognition:eu-west-1:452161433274:project/product_quality/version/product_quality.2020-07-17T09.39.14/1594971554815" --min-inference-units 1 --region eu-west-1

2. Test progammtically:
aws rekognition detect-custom-labels \
  --project-version-arn "arn:aws:rekognition:eu-west-1:452161433274:project/product_quality/version/product_quality.2020-07-17T09.39.14/1594971554815" \
  --image '{"S3Object": {"Bucket": "custom-labels-console-eu-west-1-5c5621d943","Name": "assets/casting_data/test/ok_front/cast_ok_0_10.jpeg"}}' \
  --region eu-west-1

  3. With boto3
  ```
import boto3
session = boto3.session.Session(profile_name='product_quality')
client = session.client('rekognition')
response = client.detect_custom_labels(
    ProjectVersionArn='arn:aws:rekognition:eu-west-1:452161433274:project/product_quality/version/product_quality.2020-07-17T09.39.14/1594971554815',
    Image={
        'S3Object': {
            'Bucket': 'custom-labels-console-eu-west-1-5c5621d943',
            'Name': 'assets/casting_data/test/ok_front/cast_ok_0_10.jpeg',
        }
    },
)
  ```

## Lambda Integration

![Lambda_functions_highlevel](docs/aws_highlevelarchitektur_lambdafunctions.png)


## Elastic Beanstalk

### Get right permissions
[] TODO get permission Screenshot

eb init -p python-3.7 product-quality-api --region eu-west-1

1. Create policy to access the s3 bucket and assign it the beanstalk service role:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListAllMyBuckets"
            ],
            "Resource": "arn:aws:s3:::*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::product-quality-inbound"
            ]
        }
    ]
}
```

eb create product-quality-api --profile product_quality

eb deploy



