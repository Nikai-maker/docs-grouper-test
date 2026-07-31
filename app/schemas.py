import uuid
from datetime import datetime

from pydantic import BaseModel


class FileOut(BaseModel):
    id: uuid.UUID
    download_url: str
    download_status: str
    received_at: datetime

    class Config:
        from_attributes = True


class GroupOut(BaseModel):
    id: uuid.UUID
    sender_id: int
    status: str
    created_at: datetime
    last_photo_at: datetime
    files: list[FileOut]

    class Config:
        from_attributes = True


class AckResponse(BaseModel):
    group_id: uuid.UUID
    status: str
