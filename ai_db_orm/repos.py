import uuid
from typing import TypeVar, Sequence

from sqlalchemy import create_engine, Select, Engine
from sqlmodel import Session, select, SQLModel
from google.cloud.sqlalchemy_spanner import SpannerDialect

from .models import (
    User,
    Organization,
    OrganizationUser,
    Collection,
    Resource,
    CollectionResource,
    File,
    Chat,
    ChatResource,
    ChatCollection,
    Meeting,
    MeetingRecording,
    ChatMessage,
    ResourceType,
    Website,
)
from .settings import db_settings

M = TypeVar("M", bound=SQLModel)


class CustomSpannerDialect(SpannerDialect):
    supports_native_uuid = True


class BaseRepo:
    engine: Engine
    database_url: str

    def __init__(self):
        self.engine = create_engine(
            f"spanner+spanner:///{self.database_url}",
            echo=True,
            dialect=CustomSpannerDialect(),
        )
        self.engine.dialect.supports_native_uuid = True

    def _commit_object(self, obj: M) -> M:
        with Session(self.engine) as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)

        return obj


class UserRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_USERS_URL

    def get_default_user(self) -> User:
        with Session(self.engine) as session:
            statement: Select = select(User).where(User.first_name == "Default AI", User.last_name == "service user 2")
            user = session.exec(statement).first()
            if not user:
                user = User(first_name="Default AI", last_name="service user 2")
                user = self._commit_object(user)

            return user


class OrganizationRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_ORGANIZATION_URL

    def get_default_organization(self) -> Organization:
        with Session(self.engine) as session:
            statement: Select = select(Organization).where(Organization.name == "Default AI service org 2")
            organization = session.exec(statement).first()
            if not organization:
                organization = Organization(name="Default AI service org 2")
                organization = self._commit_object(organization)

            user = UserRepo().get_default_user()
            statement: Select = select(OrganizationUser).where(OrganizationUser.user_id == user.user_id)
            organization_user = session.exec(statement).first()
            if not organization_user:
                organization_user = OrganizationUser(user_id=user.user_id, organization_id=organization.organization_id)
                self._commit_object(organization_user)

            return organization


class CollectionRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_COLLECTION_URL

    def _commit_object(self, obj):
        with Session(self.engine) as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)

        return obj

    def create_collection(self, organization_id: uuid.UUID, name: str | None = None) -> Collection:
        name = name if name else f"Collection {uuid.uuid4()}"
        collection = Collection(organization_id=organization_id, name=name)
        return self._commit_object(collection)

    def create_collection_resource(
        self, collection_id: uuid.UUID, organization_id: uuid.UUID, resource_id: uuid.UUID
    ) -> CollectionResource:
        collection_resource = CollectionResource(
            collection_id=collection_id, organization_id=organization_id, resource_id=resource_id
        )
        return self._commit_object(collection_resource)

    def get_collection_resources(self, collection_id: uuid.UUID) -> Sequence[CollectionResource]:
        with Session(self.engine) as session:
            statement: Select = select(CollectionResource).where(CollectionResource.collection_id == collection_id)
            collection_resources = session.exec(statement).all()

            return collection_resources


class ResourceRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_RESOURCES_URL

    def get_resource(self, resource_id: uuid.UUID) -> Resource:
        with Session(self.engine) as session:
            statement: Select = select(Resource).where(Resource.resource_id == resource_id)
            resource = session.exec(statement).first()
            return resource

    def create_resource(
        self, organization_id: uuid.UUID, source_entity_type: ResourceType, source_entity_id: uuid.UUID
    ) -> Resource:
        resource = Resource(
            organization_id=organization_id, source_entity_type=source_entity_type, source_entity_id=source_entity_id
        )
        resource = self._commit_object(resource)
        return resource

    def update_resource_status(self, resource_id: uuid.UUID, status: str) -> Resource:
        with Session(self.engine) as session:
            statement: Select = select(Resource).where(Resource.resource_id == resource_id)
            resource = session.exec(statement).first()
            resource.status = status
            session.add(resource)
            session.commit()

        return resource

    def get_resources_by_collection_id(self, collection_id: uuid.UUID) -> Sequence[Resource]:
        with Session(self.engine) as session:
            collection_resources = CollectionRepo().get_collection_resources(collection_id)

            statement: Select = select(Resource).where(Resource.resource_id == collection_resources[0].resource_id)
            resources = session.exec(statement).all()

            return resources

    def update_resource_ai_summary(self, resource_id: uuid.UUID, ai_summary: str) -> Resource:
        with Session(self.engine) as session:
            statement: Select = select(Resource).where(Resource.resource_id == resource_id)
            resource = session.exec(statement).first()
            resource.ai_summary = ai_summary
            session.add(resource)
            session.commit()

        return resource


class FileRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_FILES_URL

    def get_file(self, file_id: uuid.UUID) -> File:
        with Session(self.engine) as session:
            statement: Select = select(File).where(File.file_id == file_id)
            file = session.exec(statement).first()
            return file

    def create_file_for_resource(
        self, organization: Organization, resource: Resource, file_name: str, mime_type: str, user: User
    ) -> File:
        file = File(
            organization_id=organization.organization_id,
            resource_id=resource.resource_id,
            file_id=resource.source_entity_id,
            name=file_name,
            path=f"files/{resource.source_entity_id}",
            mime_type=mime_type,
            user_id=user.user_id,
        )
        file = self._commit_object(file)
        return file

    def create_file_for_meeting_recording(
        self,
        organization: Organization,
        meeting_recording: MeetingRecording,
        file_name: str,
        mime_type: str,
        user: User,
    ) -> File:
        file = File(
            organization_id=organization.organization_id,
            resource_id=meeting_recording.file_id,
            file_id=meeting_recording.file_id,
            name=file_name,
            path=f"meetings/{meeting_recording.file_id}",
            mime_type=mime_type,
            user_id=user.user_id,
        )
        file = self._commit_object(file)
        return file


class MeetingRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_MEETINGS_URL

    def create_meeting(self, organization: Organization, resource: Resource, user: User) -> Meeting:
        meeting = Meeting(
            organization_id=organization.organization_id,
            resource_id=resource.resource_id,
            user_id=user.user_id,
            meeting_id=resource.source_entity_id,
        )
        meeting = self._commit_object(meeting)
        return meeting

    def create_meeting_mixed_recording(
        self, organization_id: uuid.UUID, meeting_id: uuid.UUID, file_id: uuid.UUID
    ) -> MeetingRecording:
        meeting_recording = MeetingRecording(
            organization_id=organization_id,
            meeting_id=meeting_id,
            file_id=file_id,
            type="audio",
            subtype="mixed",
        )
        meeting_recording = self._commit_object(meeting_recording)
        return meeting_recording

    def get_meeting(self, meeting_id: uuid.UUID) -> Meeting:
        with Session(self.engine) as session:
            statement: Select = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).first()
            return meeting

    def get_meeting_recording_by_meeting_id(self, meeting_id: uuid.UUID) -> MeetingRecording:
        with Session(self.engine) as session:
            statement: Select = select(MeetingRecording).where(MeetingRecording.meeting_id == meeting_id)
            meeting_recording = session.exec(statement).first()
            return meeting_recording

    def update_meeting_transcriptions(self, meeting_id: uuid.UUID, transcriptions: str) -> Meeting:
        with Session(self.engine) as session:
            statement: Select = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).first()
            meeting.transcriptions = transcriptions
            session.add(meeting)
            session.commit()

        return meeting

    def update_meeting_recordings_transcriptions(self, meeting_id: uuid.UUID, transcriptions: str) -> MeetingRecording:
        with Session(self.engine) as session:
            statement: Select = select(MeetingRecording).where(MeetingRecording.meeting_id == meeting_id)
            meeting_recording = session.exec(statement).first()
            meeting_recording.transcriptions = transcriptions
            session.add(meeting_recording)
            session.commit()

        return meeting_recording


class WebsiteRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_WEBSITE_URL

    def get_website(self, website_id: uuid.UUID) -> Website:
        with Session(self.engine) as session:
            statement: Select = select(Website).where(Website.website_id == website_id)
            website = session.exec(statement).first()
            return website

    def create_website(self, organization: Organization, resource: Resource, user: User, url: str) -> Website:
        website = Website(
            organization_id=organization.organization_id,
            resource_id=resource.resource_id,
            user_id=user.user_id,
            name=f"Website {uuid.uuid4()}",
            website_id=resource.source_entity_id,
            url=url,
        )
        website = self._commit_object(website)
        return website

    def update_website_parsed_urls(self, website_id: uuid.UUID, parsed_urls: str) -> Website:
        with Session(self.engine) as session:
            statement: Select = select(Website).where(Website.website_id == website_id)
            website = session.exec(statement).first()
            website.parsed_urls = parsed_urls
            session.add(website)
            session.commit()

        return website


class ChatRepo(BaseRepo):

    @property
    def database_url(self) -> str:
        return db_settings.SPANNER_CHAT_URL

    def get_chat(self, chat_id: uuid.UUID, organization_id: uuid.UUID) -> Chat:
        with Session(self.engine) as session:
            statement: Select = select(Chat).where(Chat.chat_id == chat_id, Chat.organization_id == organization_id)
            chat = session.exec(statement).first()
            return chat

    def create_chat(self, organization_id: uuid.UUID, user_id: uuid.UUID, type: str, name: str) -> Chat:
        chat_id = uuid.uuid4()
        chat = Chat(organization_id=organization_id, owner_user_id=user_id, chat_id=chat_id, type=type, name=name)
        chat = self._commit_object(chat)
        return chat

    def update_chat_name(self, chat_id: uuid.UUID, name: str) -> Chat:
        with Session(self.engine) as session:
            statement: Select = select(Chat).where(Chat.chat_id == chat_id)
            chat = session.exec(statement).first()
            chat.name = name
            session.add(chat)
            session.commit()

        return chat

    def add_resource_to_chat(
        self, organization_id: uuid.UUID, chat_id: uuid.UUID, resource_id: uuid.UUID
    ) -> ChatResource:
        chat_resource = ChatResource(organization_id=organization_id, chat_id=chat_id, resource_id=resource_id)
        chat_resource = self._commit_object(chat_resource)
        return chat_resource

    def add_collection_to_chat(
        self, organization_id: uuid.UUID, chat_id: uuid.UUID, collection_id: uuid.UUID
    ) -> ChatCollection:
        chat_collection = ChatCollection(organization_id=organization_id, chat_id=chat_id, collection_id=collection_id)
        chat_collection = self._commit_object(chat_collection)
        return chat_collection

    def get_chat_resources(self, chat_id: uuid.UUID) -> Sequence[ChatResource]:
        with Session(self.engine) as session:
            statement: Select = select(ChatResource).where(ChatResource.chat_id == chat_id)
            chat_resources = session.exec(statement).all()
            return chat_resources

    def get_chat_collections(self, chat_id: uuid.UUID) -> Sequence[ChatCollection]:
        with Session(self.engine) as session:
            statement: Select = select(ChatCollection).where(ChatCollection.chat_id == chat_id)
            chat_collections = session.exec(statement).all()
            return chat_collections

    def create_chat_message(
        self,
        organization_id: uuid.UUID,
        chat_id: uuid.UUID,
        type: str,
        content: str,
        message_id: uuid.UUID | None = None,
        owner_user_id: uuid.UUID | None = None,
        arguments: dict | None = None,
    ) -> ChatMessage:
        message_id = message_id or uuid.uuid4()
        chat_message = ChatMessage(
            organization_id=organization_id,
            chat_id=chat_id,
            message_id=message_id,
            user_id=owner_user_id,
            type=type,
            content=content,
            arguments=arguments if arguments else {},
        )
        chat_message = self._commit_object(chat_message)
        return chat_message

    def get_chat_messages(self, chat_id: uuid.UUID) -> Sequence[ChatMessage]:
        with Session(self.engine) as session:
            statement: Select = (
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(40)
            )
            chat_messages = session.exec(statement).all()
            chat_messages = list(reversed(chat_messages))
            return chat_messages
