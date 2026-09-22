import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger("forensic_ai.database")

Base = declarative_base()

def get_engine():
    """Create SQLAlchemy engine with MySQL as primary and SQLite fallback if needed."""
    try:
        mysql_engine = create_engine(
            settings.DATABASE_URL,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        # Test connection immediately
        with mysql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to MySQL database at {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        return mysql_engine, "mysql"
    except Exception as exc:
        if settings.SQLITE_FALLBACK:
            sqlite_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
            logger.warning(
                f"MySQL connection to {settings.DATABASE_URL} failed ({exc}). "
                f"Falling back to local SQLite database: {sqlite_url}"
            )
            sqlite_engine = create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                echo=False
            )
            return sqlite_engine, "sqlite"
        else:
            logger.error(f"Failed to connect to MySQL and SQLITE_FALLBACK is disabled: {exc}")
            raise exc

engine, active_db_type = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> dict:
    """Check connectivity to the configured database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "type": active_db_type,
            "url": settings.DATABASE_URL if active_db_type == "mysql" else f"sqlite:///{settings.SQLITE_DB_PATH}"
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "type": active_db_type,
            "error": str(e)
        }


def init_db():
    """Initialize database tables for all registered models."""
    # Import all models to register with Base.metadata
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
