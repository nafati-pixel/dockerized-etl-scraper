is this better import os
from urllib.parse import urlparse, parse_qs, urlencode

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncGenerator, AsyncSession, create_async_engine, async_sessionmaker

load_dotenv()

_raw_url = os.getenv("DATABASE_URL")
if not _raw_url:
    raise ValueError("DATABASE_URL is not set in the environment or .env file.")

# Parse the URL properly instead of manual string splitting
_parsed = urlparse(_raw_url)
_database_path = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

_connect_args: dict[str, str] = {}

if _parsed.query:
    _database_path = _database_path.split("?")[0]
    _params = {k: v[0] for k, v in parse_qs(_parsed.query).items()}

    if "sslmode" in _params:
        _connect_args["ssl"] = _params.pop("sslmode")

    _params.pop("channel_binding", None)
    _connect_args.update(_params)


engine = create_async_engine(
    _database_path,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
or is this better
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

load_dotenv()

raw_url = os.getenv("DATABASE_URL")
if not raw_url:
    raise ValueError("No DATABASE_URL found in .env")

#adding the driver and extracting the params
Databse_Path = raw_url.replace("postgresql://", "postgresql+asyncpg://")
params_dict = {}

if "?" in raw_url:
    # --- Step A: Isolate the clean path ---
    Databse_Path = raw_url.split("?")[0].replace("postgresql://", "postgresql+asyncpg://")

    # --- Step B: Parse the params into a dict ---
    params_string = raw_url.split("?")[1]
    pairs = params_string.split("&")
    params_dict = {pair.split('=')[0]: pair.split('=')[1] for pair in pairs if '=' in pair}


    if "sslmode" in params_dict:

        params_dict["ssl"] = params_dict.pop("sslmode")
    

    params_dict.pop("channel_binding", None)


engine = create_async_engine(
    Databse_Path,
    connect_args=params_dict
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_db_session():
    async with async_session() as session: # Note: call the sessionmaker ()
        yield session
