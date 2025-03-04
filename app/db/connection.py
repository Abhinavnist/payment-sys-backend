# import psycopg2
# from psycopg2.extras import RealDictCursor
# from contextlib import contextmanager
# from app.core.config import settings
# import logging
#
# logger = logging.getLogger(__name__)
#
#
# def get_connection_string() -> str:
#     """Create PostgreSQL connection string."""
#     return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
#
#
# @contextmanager
# def get_db_connection():
#     """Context manager for database connections."""
#     conn = None
#     try:
#         # Connect to the PostgreSQL database
#         conn = psycopg2.connect(
#             host=settings.POSTGRES_SERVER,
#             port=settings.POSTGRES_PORT,
#             dbname=settings.POSTGRES_DB,
#             user=settings.POSTGRES_USER,
#             password=settings.POSTGRES_PASSWORD
#         )
#         # Yield the connection to be used
#         yield conn
#     except Exception as e:
#         logger.error(f"Database connection error: {e}")
#         raise
#     finally:
#         # Close the connection
#         if conn is not None:
#             conn.close()
#
#
# @contextmanager
# def get_db_cursor(commit=False):
#     """Context manager for database cursors."""
#     with get_db_connection() as conn:
#         # Create a cursor with RealDictCursor to return dict-like results
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         try:
#             # Yield the cursor to be used
#             yield cursor
#             # Commit the transaction if requested
#             if commit:
#                 conn.commit()
#         except Exception as e:
#             # Rollback the transaction in case of error
#             conn.rollback()
#             logger.error(f"Database query error: {e}")
#             raise
#         finally:
#             # Close the cursor
#             cursor.close()
#
#
# def execute_query(query, params=None, fetch=True, single=False, commit=True):
#     """
#     Execute a SQL query and return the results
#
#     Parameters:
#     - query: SQL query string
#     - params: Parameters for the query
#     - fetch: Whether to fetch results (SELECT) or not (INSERT/UPDATE/DELETE)
#     - single: Whether to fetch a single row or all rows
#     - commit: Whether to commit the transaction
#
#     Returns:
#     - Query results for SELECT queries
#     - None for INSERT/UPDATE/DELETE queries
#     """
#     with get_db_cursor(commit=commit) as cursor:
#         cursor.execute(query, params or {})
#
#         if fetch:
#             if single:
#                 return cursor.fetchone()
#             return cursor.fetchall()
#
#         # For INSERT operations, return the row count
#         return cursor.rowcount
#
#
# def execute_transaction(queries):
#     """
#     Execute multiple SQL queries in a single transaction
#
#     Parameters:
#     - queries: List of (query, params) tuples
#
#     Returns:
#     - None
#     """
#     with get_db_connection() as conn:
#         try:
#             with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#                 for query, params in queries:
#                     cursor.execute(query, params or {})
#             conn.commit()
#         except Exception as e:
#             conn.rollback()
#             logger.error(f"Transaction error: {e}")
#             raise

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from app.core.config import settings
import logging
import atexit

logger = logging.getLogger(__name__)

# Create a global connection pool that will be shared across the application
connection_pool = None


def initialize_connection_pool():
    """Initialize the PostgreSQL connection pool."""
    global connection_pool

    try:
        connection_pool = pool.ThreadedConnectionPool(
            minconn=5,  # Minimum number of connections in the pool
            maxconn=20,  # Maximum number of connections in the pool
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        logger.info("PostgreSQL connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing connection pool: {e}")
        raise


def close_connection_pool():
    """Close all connections in the pool."""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logger.info("PostgreSQL connection pool closed")


# Register the close_connection_pool function to run when the application exits
atexit.register(close_connection_pool)


def get_connection_string() -> str:
    """Create PostgreSQL connection string."""
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


@contextmanager
def get_db_connection():
    """Context manager for database connections from the pool."""
    global connection_pool

    # Initialize the connection pool if it doesn't exist yet
    if connection_pool is None:
        initialize_connection_pool()

    conn = None
    try:
        # Get a connection from the pool
        conn = connection_pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        # Return the connection to the pool
        if conn is not None:
            connection_pool.putconn(conn)


@contextmanager
def get_db_cursor(commit=False):
    """Context manager for database cursors."""
    with get_db_connection() as conn:
        # Create a cursor with RealDictCursor to return dict-like results
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Yield the cursor to be used
            yield cursor
            # Commit the transaction if requested
            if commit:
                conn.commit()
        except Exception as e:
            # Rollback the transaction in case of error
            conn.rollback()
            logger.error(f"Database query error: {e}")
            raise
        finally:
            # Close the cursor
            cursor.close()


def execute_query(query, params=None, fetch=True, single=False, commit=True):
    """
    Execute a SQL query and return the results

    Parameters:
    - query: SQL query string
    - params: Parameters for the query
    - fetch: Whether to fetch results (SELECT) or not (INSERT/UPDATE/DELETE)
    - single: Whether to fetch a single row or all rows
    - commit: Whether to commit the transaction

    Returns:
    - Query results for SELECT queries
    - None for INSERT/UPDATE/DELETE queries
    """
    with get_db_cursor(commit=commit) as cursor:
        cursor.execute(query, params or {})

        if fetch:
            if single:
                return cursor.fetchone()
            return cursor.fetchall()

        # For INSERT operations, return the row count
        return cursor.rowcount


def execute_transaction(queries):
    """
    Execute multiple SQL queries in a single transaction

    Parameters:
    - queries: List of (query, params) tuples

    Returns:
    - None
    """
    with get_db_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for query, params in queries:
                    cursor.execute(query, params or {})
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction error: {e}")
            raise