import re
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field, SQLModel
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.declarative import declared_attr
from typing import Optional
import uuid
from sqlalchemy.types import TypeDecorator, String

from enums import ResourceType, ResourceStatus


class UUIDString(TypeDecorator):
    impl = String(36)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value


class BaseTable(SQLModel):
    updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        name = cls.__name__
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        name += "s"

        return name


class BaseOrganizationTable(BaseTable):
    organization_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)


class User(BaseTable, table=True):
    user_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    first_name: str
    last_name: str
    phone: str = "doesnt matter"
    email: str = "doesnt matter"
    password: str = "doesnt matter"


class Organization(BaseOrganizationTable, table=True):
    name: str
    timezone: str = "doesnt matter"
    status: str = "doesnt matter"


class OrganizationUser(BaseOrganizationTable, table=True):
    user_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    status: str = "doesnt matter"


class Collection(BaseOrganizationTable, table=True):
    collection_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    name: str
    color_code: str = "#000000"
    description: Optional[str] = None


class CollectionResource(BaseOrganizationTable, table=True):
    collection_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    resource_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)


class Resource(BaseOrganizationTable, table=True):
    resource_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    source_entity_type: ResourceType
    source_entity_id: uuid.UUID = Field(sa_type=UUIDString)
    status: ResourceStatus = ResourceStatus.pending
    name: str = ""
    ai_summary: str | None = ""


class File(BaseOrganizationTable, table=True):
    file_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(sa_type=UUIDString)
    name: str
    path: str
    mime_type: str
    user_id: uuid.UUID = Field(sa_type=UUIDString)
    deleted: bool | None = None


class Meeting(BaseOrganizationTable, table=True):
    meeting_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(
        sa_type=UUIDString,
    )
    provider_meeting_id: str | None = None
    provider_meeting_password: str | None = None
    provider_meeting_url: str | None = None
    provider: str = "doesnt matter"
    status: str = "pending"
    status_updated_at: datetime = Field(default_factory=datetime.now)
    transcriptions: str | None = None
    user_id: uuid.UUID = Field(
        sa_type=UUIDString,
    )


class MeetingParticipant(BaseOrganizationTable, table=True):
    meeting_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    participant_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    name: str
    joined_at: datetime | None = None
    left_at: datetime | None = None


class MeetingRecording(BaseOrganizationTable, table=True):
    meeting_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    recording_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    participant_id: uuid.UUID | None = Field()
    file_id: uuid.UUID = Field(
        sa_type=UUIDString,
    )
    type: str  # -- Specifies "audio" or "video".
    subtype: str  # -- Specifies the audio subtype: "mixed", "one-way", "share", "interpreter".
    transcriptions: str | None = None
    started_at: datetime | None = None


class Website(BaseOrganizationTable, table=True):
    website_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(
        sa_type=UUIDString,
    )
    name: str
    url: str
    parsed_urls: str | None = None
    user_id: uuid.UUID | None = Field(
        sa_type=UUIDString,
    )


class Chat(BaseOrganizationTable, table=True):
    chat_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    owner_user_id: uuid.UUID = Field(
        sa_type=UUIDString,
    )
    type: str
    summary: Optional[str] = None
    name: str


class ChatCollection(BaseOrganizationTable, table=True):
    chat_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    collection_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)


class ChatUser(BaseOrganizationTable, table=True):
    chat_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    user_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)


class ChatResource(BaseOrganizationTable, table=True):
    chat_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    resource_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)


class ChatMessage(BaseOrganizationTable, table=True):
    chat_id: uuid.UUID = Field(sa_type=UUIDString, primary_key=True)
    message_id: uuid.UUID = Field(sa_type=UUIDString, default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field()
    type: str
    content: str
    arguments: dict = Field(sa_column=Column(JSON))
    is_summarized: bool = False
