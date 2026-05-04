import logging
import os
from contextlib import contextmanager
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder

from .config import DB, SSH

logger = logging.getLogger(__name__)


@contextmanager
def _tunnel():
    logger.debug("Abriendo túnel SSH hacia %s:%s", SSH.host, SSH.port)
    tunnel = SSHTunnelForwarder(
        (SSH.host, SSH.port),
        ssh_username=SSH.username,
        ssh_password=SSH.password,
        remote_bind_address=(DB.host, DB.port),
    )
    tunnel.start()
    try:
        yield tunnel
    finally:
        tunnel.stop()
        logger.debug("Túnel SSH cerrado")


@contextmanager
def get_connection():
    with _tunnel() as tunnel:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=tunnel.local_bind_port,
            database=DB.database,
            user=DB.username,
            password=DB.password,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()


def fetch_pending_employees() -> list[dict]:
    today = date.today()
    lookback_days = int(os.getenv("LOOKBACK_DAYS", "15"))
    cutoff = today - timedelta(days=lookback_days)

    query = """
        SELECT id, full_name, name_role, active_since
        FROM rh.employees
        WHERE active_since >= %s
          AND active_since <= %s
        ORDER BY active_since;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (cutoff, today))
            rows = cur.fetchall()
            logger.info(
                "Rango evaluado: %s → %s | Registros encontrados: %d",
                cutoff, today, len(rows),
            )
            return [dict(r) for r in rows]
