from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AwsCredentials(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str] = None


class DeployRequest(BaseModel):
    bucket_name: str = Field(default="dbx-bucket-testing", min_length=3, max_length=63)
    backend: Optional[AwsCredentials] = None
    deployment: Optional[AwsCredentials] = None
