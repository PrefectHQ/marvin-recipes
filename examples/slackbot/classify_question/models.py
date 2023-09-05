from uuid import uuid4

from pydantic import BaseModel, Field


class MetricRecord(BaseModel):
    class Config:
        orm_mode = True

    id: str = Field(default_factory=lambda: str(uuid4()))
    concept: str
    count: int
