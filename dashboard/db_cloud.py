"""
db_cloud.py
-----------
Unified database layer — works with both:
  - Local SQLite (development / your PC)
  - Supabase PostgreSQL (production / Streamlit Cloud)

Automatically detects which to use based on environment variable SUPABASE_URL.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# ── Connection detection ──────────────────────────────────────────────────────

def _get_supabase_url():
    """Get Supabase URL from environment or Streamlit secrets."""
    # 1. Environment variable
    url = os.environ.get("SUPABASE_URL", "")
    if url:
        return url

    # 2. Streamlit secrets (when deployed on Streamlit Cloud)
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        if url:
            return url
    except Exception:
        pass

    return ""


def _get_sqlite_path():
    """Find the SQLite DB path."""
    # Try relative paths
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "data", "trade_tradestat.db"),
        os.path.join(os.path.dirname(__file__), "..", "data", "trade.db"),
        "data/trade_tradestat.db",
        "data/trade.db",
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def is_cloud() -> bool:
    """Returns True if Supabase URL is configured."""
    return bool(_get_supabase_url())


# ── Query function ────────────────────────────────────────────────────────────

def q(sql: str, params: tuple = (), db_path: str = None) -> pd.DataFrame:
    """
    Run SQL query against whichever database is configured.
    Automatically uses Supabase if SUPABASE_URL is set, otherwise SQLite.
    """
    supabase_url = _get_supabase_url()

    if supabase_url:
        return _q_postgres(sql, params, supabase_url)
    else:
        sqlite_path = db_path or _get_sqlite_path()
        if not sqlite_path:
            logger.error("No database found. Run: python main.py --process")
            return pd.DataFrame()
        return _q_sqlite(sql, params, sqlite_path)


def _q_sqlite(sql: str, params: tuple, db_path: str) -> pd.DataFrame:
    import sqlite3
    with sqlite3.connect(db_path, timeout=30) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def _q_postgres(sql: str, params: tuple, url: str) -> pd.DataFrame:
    """Query PostgreSQL (Supabase). Converts SQLite ? to named :p0,:p1,... params."""
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)

        # Convert ? placeholders to :p0, :p1, ... for SQLAlchemy
        named_sql = sql
        param_dict = {}
        for i, v in enumerate(params):
            named_sql = named_sql.replace("?", f":p{i}", 1)
            param_dict[f"p{i}"] = v

        with engine.connect() as conn:
            result = conn.execute(text(named_sql), param_dict)
            rows = result.fetchall()
            cols = list(result.keys())
            return pd.DataFrame(rows, columns=cols)

    except Exception as e:
        logger.error(f"PostgreSQL query failed: {e}")
        logger.error(f"SQL was: {sql[:120]}")
        return pd.DataFrame()


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Get database statistics."""
    try:
        cxc_rows  = q("SELECT COUNT(*) AS n FROM cxc").iloc[0,0]
        hs_codes  = q("SELECT COUNT(DISTINCT hs_code) AS n FROM cxc").iloc[0,0]
        countries = q("SELECT COUNT(DISTINCT country) AS n FROM cxc").iloc[0,0]
        date_rng  = q("SELECT MIN(date)||' to '||MAX(date) AS r FROM cxc").iloc[0,0]
        return dict(cxc_rows=int(cxc_rows), hs_codes=int(hs_codes),
                    countries=int(countries), date_range=str(date_rng),
                    backend="supabase" if is_cloud() else "sqlite")
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return dict(cxc_rows=0, hs_codes=0, countries=0,
                    date_range="none", backend="error")
