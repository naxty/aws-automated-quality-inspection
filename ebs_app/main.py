import os
from typing import List
from enum import Enum

import boto3
import botocore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from cryptography.fernet import Fernet

key = Fernet.generate_key()
f = Fernet(key)
BUCKET = os.environ["BUCKET"]
session = boto3.session.Session()

s3 = session.client("s3")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


class NeedDecision(BaseModel):
    name: str
    blob_name: str


class NeedDecisionResponse(BaseModel):
    need_decisions: List[NeedDecision]


class DecisionEnum(str, Enum):
    ok = "ok"
    defect = "defect"


class Decision(BaseModel):
    id: str
    decision: DecisionEnum


@app.get("/need_decision", response_model=dict)
def get_need_decision_images():
    response = s3.list_objects(Bucket=BUCKET, Prefix="unclear/",)
    if "Contents" not in response:
        return {}
    blobs = response["Contents"]
    return_blob = None

    for blob in blobs:
        if ".jpeg" in blob["Key"] or ".jpg" in blob["Key"]:
            return_blob = blob
            break
    if not return_blob:
        return {}
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": return_blob["Key"]}, ExpiresIn=10
    )
    return {"url": url, "id": f.encrypt(str.encode(return_blob["Key"])).decode("utf-8")}


@app.post("/make_decision")
def make_decision(decision: Decision):
    token = decision.id.encode("utf-8")
    decrypted_blob_name = f.decrypt(token).decode("utf-8")
    try:
        s3.head_object(Bucket=BUCKET, Key=decrypted_blob_name)
    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=404, detail="Blob not found")

    value = decision.decision
    _, name = os.path.split(decrypted_blob_name)
    new_blob_name = f"{value}_{name}"

    s3.copy_object(
        Bucket=BUCKET,
        Key=f"human_decided/{new_blob_name}",
        CopySource={"Bucket": BUCKET, "Key": decrypted_blob_name}
    )
    s3.delete_object(Bucket=BUCKET, Key=decrypted_blob_name)
    return 200


@app.get("/.*", include_in_schema=False)
def root():
    return FileResponse("./static/index.html")
