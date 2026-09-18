"""
Manual database initialization script.
Creates all tables in PostgreSQL using SQLAlchemy models.
"""
import logging
from sqlalchemy import create_engine
from app.db.models import Base
from app.config.settings import settings

logger = logging.getLogger(__name__)


def init_database():
    """Initialize the database with all tables."""
    try:
        engine = create_engine(settings.postgres_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("Database initialized successfully")
        logger.info(f"Connected to: {settings.postgres_url}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
