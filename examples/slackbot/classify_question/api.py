from uuid import uuid4

import pydantic
from db import inject_db, metrics
from models import MetricRecord
from sqlalchemy import select


@inject_db
async def update_metrics(session, concepts: set[str]):
    async with session.begin():
        for concept in concepts:
            existing_count = await session.execute(
                select(metrics.c.count).where(metrics.c.concept == concept)
            )
            existing_count = existing_count.scalar_one_or_none()
            new_count = existing_count + 1 if existing_count else 1
            values = {"id": str(uuid4()), "concept": concept, "count": new_count}
            await session.execute(
                metrics.insert().prefix_with("OR REPLACE").values(values)
            )


@inject_db
async def read_metrics(session) -> list[MetricRecord]:
    async with session.begin():
        result = await session.execute(select(metrics))
        return pydantic.parse_obj_as(list[MetricRecord], result.all())
