#!/usr/bin/env bash

set -a
. ./config
set +a

## upload pics to inbound bucket
aws s3 cp data/sample_pics/test_pic_ok.jpeg s3://"${INBOUND_BUCKET}"/test_pic_ok.jpeg
aws s3 cp data/sample_pics/test_pic_def.jpeg s3://"${INBOUND_BUCKET}"/test_pic_def.jpeg

## wait a little for processing
sleep 60

### delete pics from bucket in case of failure
aws s3 rm s3://"${INBOUND_BUCKET}" --recursive


