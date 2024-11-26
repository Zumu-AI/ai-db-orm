from enum import StrEnum


class ResourceType(StrEnum):
    file = "file"
    meeting = "meeting"
    website = "website"


class ResourceStatus(StrEnum):
    pending = "pending"
    failed = "failed"
    available = "available"
