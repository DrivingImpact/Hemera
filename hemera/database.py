"""Database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from hemera.config import get_settings

settings = get_settings()

# Neon requires SSL; the connection string includes ?sslmode=require
# SQLAlchemy handles this via the URL parameters
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # verify connections before use (handles Neon cold starts)
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
