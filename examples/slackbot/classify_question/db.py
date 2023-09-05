from functools import wraps

from sqlalchemy import Column, Integer, MetaData, String, Table
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
            kwargs["session"] = session
            return await fn(*args, **kwargs)

    return wrapper
