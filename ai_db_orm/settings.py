import os
from typing import Annotated

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from google.cloud import secretmanager


class OnCloud:
    """A marker class for secrets that are stored on the cloud."""


class DBSettings(BaseSettings):
    SPANNER_USERS_URL: Annotated[str, OnCloud]
    SPANNER_ORGANIZATION_URL: Annotated[str, OnCloud]
    SPANNER_COLLECTION_URL: Annotated[str, OnCloud]
    SPANNER_RESOURCES_URL: Annotated[str, OnCloud]
    SPANNER_FILES_URL: Annotated[str, OnCloud]
    SPANNER_MEETINGS_URL: Annotated[str, OnCloud]
    SPANNER_CHAT_URL: Annotated[str, OnCloud]
    SPANNER_WEBSITE_URL: Annotated[str, OnCloud]
    SPANNER_ASSISTANT_URL: Annotated[str, OnCloud]


def load_secrets(environ: str):
    client = secretmanager.SecretManagerServiceClient()

    if environ == "production":
        project_id = "zumu-ai-production"
    else:
        project_id = "zumu-ai-staging"

    for name, field_info in DBSettings.model_fields.items():
        if OnCloud in field_info.metadata:
            secret_name = f"projects/{project_id}/secrets/{name.lower()}/versions/latest"
            response = client.access_secret_version(name=secret_name)
            secret_data = response.payload.data.decode("UTF-8")
            os.environ[name] = secret_data.strip()

env = os.environ.get("ENV")

if env == "production" or env == "staging":
    load_secrets(env)
else:
    load_dotenv(override=True)

db_settings = DBSettings()

__all__ = ["db_settings"]
