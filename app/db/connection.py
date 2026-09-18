"""
PostgreSQL connection management with connection pooling.
"""
import logging
from typing import Optional
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor
from app.config.settings import settings

logger = logging.getLogger(__name__)


class PostgresConnectionPool:
    """Thread-safe connection pool for PostgreSQL."""
    
    _instance: Optional['PostgresConnectionPool'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self) -> bool:
        """Initialize the connection pool."""
        if self._pool is not None:
            return True
        
        try:
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=settings.POSTGRES_POOL_SIZE,
                dsn=settings.postgres_url,
                cursor_factory=DictCursor
            )
            logger.info("PostgreSQL connection pool initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            return False
    
    def get_connection(self):
        """Get a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        return self._pool.getconn()
    
    def return_connection(self, conn):
        """Return a connection to the pool."""
        if self._pool is not None:
            self._pool.putconn(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")
    
    def is_available(self) -> bool:
        """Check if PostgreSQL is available."""
        if self._pool is None:
            return False
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            self.return_connection(conn)
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL availability check failed: {e}")
            return False


def get_postgres_pool() -> PostgresConnectionPool:
    """Get the singleton PostgreSQL connection pool."""
    pool = PostgresConnectionPool()
    if pool._pool is None:
        pool.initialize()
    return pool
