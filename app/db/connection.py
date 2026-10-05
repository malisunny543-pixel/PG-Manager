import os
import queue
import threading
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from flask import current_app, g

class PyMySQLConnectionPool:
    """Thread-safe connection pool for PyMySQL without external ORM dependencies."""
    def __init__(self, host, port, user, password, database, charset='utf8mb4', max_connections=10, ssl_ca=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.max_connections = max_connections
        self.ssl_ca = ssl_ca
        self._pool = queue.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()

    def _create_connection(self):
        connect_kwargs = {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': self.database,
            'charset': self.charset,
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False
        }
        if self.ssl_ca and os.path.exists(self.ssl_ca):
            connect_kwargs['ssl'] = {'ca': self.ssl_ca}
        return pymysql.connect(**connect_kwargs)

    def get_connection(self, timeout=10):
        """Borrow a connection from the pool or create a new one if below max_connections."""
        try:
            conn = self._pool.get_nowait()
            try:
                conn.ping()
            except Exception:
                conn = self._create_connection()
            return conn
        except queue.Empty:
            with self._lock:
                if self._created_connections < self.max_connections:
                    self._created_connections += 1
                    return self._create_connection()
            conn = self._pool.get(block=True, timeout=timeout)
            try:
                conn.ping()
            except Exception:
                conn = self._create_connection()
            return conn

    def release_connection(self, conn):
        """Return a borrowed connection back to the pool in a clean rollback state."""
        if conn is not None and conn.open:
            try:
                conn.rollback()
                self._pool.put_nowait(conn)
            except (queue.Full, Exception):
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._created_connections = max(0, self._created_connections - 1)

    def close_all(self):
        """Close all pooled connections."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                if conn and conn.open:
                    conn.close()
            except Exception:
                pass
        with self._lock:
            self._created_connections = 0


_global_pool = None
_pool_lock = threading.Lock()

def get_pool(app=None):
    """Retrieve or initialize the singleton connection pool for the application."""
    global _global_pool
    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                if app is None:
                    app = current_app
                config = app.config
                _global_pool = PyMySQLConnectionPool(
                    host=config['DB_HOST'],
                    port=config['DB_PORT'],
                    user=config['DB_USER'],
                    password=config['DB_PASSWORD'],
                    database=config['DB_NAME'],
                    charset=config['DB_CHARSET'],
                    max_connections=config['DB_POOL_SIZE'],
                    ssl_ca=config.get('DB_SSL_CA')
                )
    return _global_pool


def get_db():
    """Retrieve or borrow a PyMySQL connection from the pool for the current request context."""
    if '_database' not in g:
        pool = get_pool(current_app)
        g._database = pool.get_connection()
    return g._database


def close_db(e=None):
    """Return the borrowed connection back to the pool at the end of the request context."""
    db = g.pop('_database', None)
    if db is not None:
        pool = get_pool(current_app)
        pool.release_connection(db)


def init_db(app):
    """Register database teardown with Flask application."""
    app.teardown_appcontext(close_db)


def query_db(query, args=(), one=False):
    """Execute a parameterized SELECT query and return rows as dictionaries."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), commit=True):
    """Execute a parameterized INSERT, UPDATE, or DELETE query.
    Returns a dict with 'lastrowid' and 'rowcount'.
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(query, args)
        result = {
            'lastrowid': cursor.lastrowid,
            'rowcount': cursor.rowcount
        }
    if commit:
        db.commit()
    return result


@contextmanager
def db_transaction():
    """Context manager for explicit multi-statement atomic transactions.
    Supports SELECT ... FOR UPDATE row-level locking.
    Automatically commits on success or rolls back on exception.
    """
    db = get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
