"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from src.config.settings import config
from src.database.models import Base


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        """Initialize database manager."""
        self.engine = create_engine(
            config.database.url,
            echo=config.database.echo
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """
        Get a database session (manual cleanup required).
        
        Returns:
            Session: SQLAlchemy session
        """
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()