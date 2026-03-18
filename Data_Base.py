import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

load_dotenv()

raw_url = os.getenv("DATABASE_URL")
if not raw_url:
    raise ValueError("No DATABASE_URL found in .env")

# --- FIX 1: Define defaults OUTSIDE the if-block (Scope safety) ---
# We assume there are no params first.
Databse_Path = raw_url.replace("postgresql://", "postgresql+asyncpg://")
params_dict = {}

if "?" in raw_url:
    # --- Step A: Isolate the clean path ---
    Databse_Path = raw_url.split("?")[0].replace("postgresql://", "postgresql+asyncpg://")

    # --- Step B: Parse the params into a dict ---
    params_string = raw_url.split("?")[1]
    pairs = params_string.split("&")
    params_dict = {pair.split('=')[0]: pair.split('=')[1] for pair in pairs if '=' in pair}

    # --- FIX 2: Translate keys for asyncpg compatibility ---
    if "sslmode" in params_dict:
        # Move the value from 'sslmode' (bad) to 'ssl' (good)
        params_dict["ssl"] = params_dict.pop("sslmode")
    
    # Remove other keys that asyncpg might reject
    params_dict.pop("channel_binding", None)

# Now it is safe to create the engine
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
