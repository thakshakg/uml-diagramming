import os
from sqlmodel import create_engine, SQLModel, Session # Session for sync, AsyncSession for async
from sqlmodel.ext.asyncio.session import AsyncSession # Import AsyncSession correctly
from sqlalchemy.ext.asyncio import create_async_engine # For creating async engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://uml_user:secret@localhost/uml_db")
# The DATABASE_URL from docker-compose.yml is "postgresql://uml_user:secret@db/uml_db"
# For asyncpg, it should be "postgresql+asyncpg://uml_user:secret@db/uml_db"

# Create an async engine
async_engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async def init_db():
    async with async_engine.begin() as conn:
        # For now, we'll use SQLModel.metadata.create_all.
        # In a production app, you'd use Alembic migrations.
        # await conn.run_sync(SQLModel.metadata.drop_all) # Use with caution
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_async_session() -> AsyncSession: # type: ignore
    async_session_maker = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

# If you need a synchronous session for Alembic or certain scripts:
# SYNC_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://uml_user:secret@localhost/uml_db").replace("postgresql+asyncpg", "postgresql")
# sync_engine = create_engine(SYNC_DATABASE_URL, echo=True)

# def get_session():
#     with Session(sync_engine) as session:
#         yield session
