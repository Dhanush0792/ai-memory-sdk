"""
Database connection management with connection pooling.
"""

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from typing import Generator
from app.config import settings


class Database:
    """PostgreSQL database connection manager."""
    
    def __init__(self):
        self.connection_string = settings.database_url
        self._pool = None
    
    def initialize(self):
        """Initialize database connection pool."""
        try:
            # Create connection pool
            self._pool = ConnectionPool(
                conninfo=self.connection_string,
                min_size=2,
                max_size=10,
                timeout=30
            )
            print("✓ Database connection pool initialized")
        except Exception as e:
            print(f"✗ Failed to initialize database: {e}")
            raise
    
    def close(self):
        """Close database connection pool."""
        if self._pool:
            self._pool.close()
            print("✓ Database connection pool closed")
    
    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
        """
        Get a database connection from the pool.
        
        Usage:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM memories")
        """
        if not self._pool:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        with self._pool.connection() as conn:
            yield conn
    
    @contextmanager
    def get_cursor(self, row_factory=dict_row) -> Generator[psycopg.Cursor, None, None]:
        """
        Get a database cursor with automatic connection management.
        
        Usage:
            with db.get_cursor() as cur:
                cur.execute("SELECT * FROM memories")
                results = cur.fetchall()
        """
        with self.get_connection() as conn:
            with conn.cursor(row_factory=row_factory) as cur:
                yield cur
    
    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False


# Global database instance
db = Database()
