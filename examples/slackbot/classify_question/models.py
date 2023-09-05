import re
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class MetricRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    concept: str
    count: int
    slug: str

    @validator("slug", always=True)
    def verify_slug(cls, v, values):
        LOWERCASE_AND_HYPHENS = re.compile(r"^[a-z0-9-]+$")
        if not LOWERCASE_AND_HYPHENS.match(v):
            raise ValueError(
                "slug must only contain lowercase alphanumeric characters and hyphens"
            )
        return v
