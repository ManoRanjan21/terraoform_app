from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
from typing import Optional

from app.models import AwsCredentials

BACKEND_PROFILE = "dbx-test-user"
AWS_CREDENTIALS_PATH = Path.home() / ".aws" / "credentials"


def write_backend_profile(creds: AwsCredentials, path: Path = AWS_CREDENTIALS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    parser = ConfigParser()
    if path.exists():
        parser.read(path)

    if not parser.has_section(BACKEND_PROFILE):
        parser.add_section(BACKEND_PROFILE)

    parser.set(BACKEND_PROFILE, "aws_access_key_id", creds.aws_access_key_id)
    parser.set(BACKEND_PROFILE, "aws_secret_access_key", creds.aws_secret_access_key)

    if creds.aws_session_token:
        parser.set(BACKEND_PROFILE, "aws_session_token", creds.aws_session_token)
    elif parser.has_option(BACKEND_PROFILE, "aws_session_token"):
        parser.remove_option(BACKEND_PROFILE, "aws_session_token")

    with path.open("w") as handle:
        parser.write(handle)


def deployment_env(creds: Optional[AwsCredentials], base_env: Optional[dict] = None) -> dict:
    env = dict(base_env or {})
    if creds is None:
        env.pop("AWS_PROFILE", None)
        env.pop("AWS_DEFAULT_PROFILE", None)
        return env

    env["AWS_ACCESS_KEY_ID"] = creds.aws_access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = creds.aws_secret_access_key

    if creds.aws_session_token:
        env["AWS_SESSION_TOKEN"] = creds.aws_session_token
    else:
        env.pop("AWS_SESSION_TOKEN", None)

    env.pop("AWS_PROFILE", None)
    env.pop("AWS_DEFAULT_PROFILE", None)
    return env
