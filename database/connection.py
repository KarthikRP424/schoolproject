"""
database/connection.py
----------------------
Database connection and transaction manager using context managers.
Designed to be compatible with both SQLite (development) and MySQL (production).
"""
import sqlite3
import contextlib
import config

@contextlib.contextmanager
def get_db_connection():
    """
    Context manager that handles connection lifecycle and transactions.
    Rolls back automatically on exception, commits on success.
    """
    if config.DB_TYPE == "sqlite":
        conn = sqlite3.connect(config.SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # Enables dictionary-like row access
        conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    elif config.DB_TYPE == "mysql":
        # Pre-configured MySQL context block for seamless migration
        import mysql.connector
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    else:
        raise ValueError(f"Invalid DB_TYPE configuration: {config.DB_TYPE}")

def execute_query(query: str, params: tuple = (), fetch: str = "all"):
    """
    Helper function to run a SQL query within a transaction context.
    Returns: List of dicts for 'all', single dict/None for 'one', int for 'lastrowid' or 'rowcount'.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == "all":
            rows = cursor.fetchall()
            return [dict(r) for r in rows] if rows else []
        elif fetch == "one":
            row = cursor.fetchone()
            return dict(row) if row else None
        elif fetch == "lastrowid":
            return cursor.lastrowid
        else:
            return cursor.rowcount
