from functools import wraps
from uuid import uuid4

from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

metadata = MetaData()
metrics = Table(
    "metrics",
    metadata,
    Column("id", String, primary_key=True),
    Column("concept", String, unique=True),
    Column("count", Integer),
)
queries = Table(
    "queries",
    metadata,
    Column("id", String, primary_key=True),
    Column("query_text", String),
)

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


def inject_db(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        AsyncSessionLocal = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with AsyncSessionLocal() as session:
            kwargs["db"] = engine
            kwargs["session"] = session
            return await fn(*args, **kwargs)

    return wrapper


@inject_db
async def update_metrics(db, session, concepts: set[str]):
    async with session.begin():  # Using the session
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
async def read_metrics(db, session):
    async with session.begin():  # Using the session
        result = await session.execute(select(metrics))
        return result.scalars().all()
