"""Database engine and session factory, configured from DATABASE_URL."""

import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

_raw_url = os.getenv("DATABASE_URL")
if not _raw_url:
    raise ValueError("DATABASE_URL is not set in the environment or .env file.")

_parsed = urlparse(_raw_url)
_connect_args: dict[str, str] = {}

if _parsed.query:
    _query_params = {key: values[0] for key, values in parse_qs(_parsed.query).items()}

    if "sslmode" in _query_params:
        _connect_args["ssl"] = _query_params.pop("sslmode")

    _query_params.pop("channel_binding", None)
    _connect_args.update(_query_params)

_database_url = urlunparse(_parsed._replace(scheme="postgresql+asyncpg", query=""))

engine = create_async_engine(
    _database_url,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-style dependency that yields a request-scoped DB session."""
    async with async_session() as session:
        yield session
