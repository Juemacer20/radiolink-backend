from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from uuid import uuid4

DATABASE_URL = "sqlite+aiosqlite:///./radiolinks.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class RadioLinkDB(Base):
    __tablename__ = "radio_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    lat_a = Column(Float, nullable=False)
    lon_a = Column(Float, nullable=False)
    height_a = Column(Float, nullable=False)
    lat_b = Column(Float, nullable=False)
    lon_b = Column(Float, nullable=False)
    height_b = Column(Float, nullable=False)
    frequency_ghz = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
