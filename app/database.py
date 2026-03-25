"""Database configuration and session management"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import Base from models to ensure all models are registered before table creation
from app.models import Base

# Database URL - using SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance_monitor.db")

# Create engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.models import Base

    Base.metadata.create_all(bind=engine)
