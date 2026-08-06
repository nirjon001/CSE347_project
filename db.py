import mysql.connector
from flask import g, has_app_context

from config import DB_CONFIG


def _open():
    conn = mysql.connector.connect(connection_timeout=15, **DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
    cur.close()
    return conn


def get_connection():
    conn = getattr(g, '_db_conn', None) if has_app_context() else None
    if conn is None:
        conn = _open()
        if has_app_context():
            g._db_conn = conn
    return conn


def get_dedicated_connection():
    return _open()


def init_db(app):
    @app.teardown_appcontext
    def _teardown(exc):
        conn = g.pop('_db_conn', None)
        if conn is not None:
            conn.close()


def query(sql, params=(), one=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if not has_app_context():
        conn.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    if not has_app_context():
        conn.close()
    return last_id
