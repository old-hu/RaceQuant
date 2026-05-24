from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_engine() -> Engine:
    global engine
    if engine is None:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Generator:
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
