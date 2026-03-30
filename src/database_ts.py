"""database_ts.py - SQLite for all 3 tradestat file types."""
import os, sqlite3, logging
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def conn(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    c = sqlite3.connect(db_path, timeout=60)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA cache_size=-64000")
    c.row_factory = sqlite3.Row
    try: yield c; c.commit()
    except: c.rollback(); raise
    finally: c.close()

def init_db(db_path):
    with conn(db_path) as c:
        # Commodity totals (all countries combined)
        c.execute("""CREATE TABLE IF NOT EXISTS commodity (
            date TEXT, year INT, month TEXT, month_num INT,
            hs_code TEXT, hs_description TEXT,
            export_usd_mn REAL DEFAULT 0, import_usd_mn REAL DEFAULT 0,
            PRIMARY KEY(date, hs_code, month_num))""")
        # Country totals (all commodities combined)
        c.execute("""CREATE TABLE IF NOT EXISTS country (
            date TEXT, year INT, month TEXT, month_num INT, country TEXT,
            export_usd_mn REAL DEFAULT 0, import_usd_mn REAL DEFAULT 0,
            PRIMARY KEY(date, country))""")
        # CXC: HS4 × Country (the core cross-tab)
        c.execute("""CREATE TABLE IF NOT EXISTS cxc (
            date TEXT, year INT, month TEXT, month_num INT,
            hs_code TEXT, hs_description TEXT, country TEXT,
            export_usd_mn REAL DEFAULT 0, import_usd_mn REAL DEFAULT 0,
            export_share_pct REAL DEFAULT 0, import_share_pct REAL DEFAULT 0,
            PRIMARY KEY(date, hs_code, country))""")
        for tbl,col in [("commodity","hs_code"),("country","country"),("cxc","hs_code")]:
            c.execute(f"CREATE INDEX IF NOT EXISTS ix_{tbl}_date ON {tbl}(date)")
            c.execute(f"CREATE INDEX IF NOT EXISTS ix_{tbl}_{col} ON {tbl}({col})")
    logger.info(f"DB ready: {db_path}")

def _bulk_insert(df, table, key_cols, db_path):
    """Fast bulk insert using executemany."""
    if df.empty: return 0
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cols    = [c for c in df.columns if c in key_cols + 
               [c for c in df.columns if c not in ["id"]]]
    ph      = ",".join("?" * len(cols))
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c not in key_cols)
    sql     = (f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph}) "
               f"ON CONFLICT({','.join(key_cols)}) DO UPDATE SET {updates}")
    rows = [tuple(row[c] for c in cols) for _, row in df[cols].iterrows()]
    with conn(db_path) as c:
        c.executemany(sql, rows)
    return len(rows)

def upsert_commodity(df, db_path):
    cols = ["date","year","month","month_num","hs_code","hs_description",
            "export_usd_mn","import_usd_mn"]
    return _bulk_insert(df[[c for c in cols if c in df.columns]], "commodity",
                        ["date","hs_code","month_num"], db_path)

def upsert_country(df, db_path):
    cols = ["date","year","month","month_num","country",
            "export_usd_mn","import_usd_mn"]
    return _bulk_insert(df[[c for c in cols if c in df.columns]], "country",
                        ["date","country"], db_path)

def upsert_cxc(df, db_path):
    cols = ["date","year","month","month_num","hs_code","hs_description","country",
            "export_usd_mn","import_usd_mn","export_share_pct","import_share_pct"]
    return _bulk_insert(df[[c for c in cols if c in df.columns]], "cxc",
                        ["date","hs_code","country"], db_path)

def q(sql, params=(), db_path=None):
    with conn(db_path) as c:
        return pd.read_sql_query(sql, c, params=params)

def get_commodity_df(db_path):
    if not os.path.exists(db_path): return pd.DataFrame()
    df = q("SELECT * FROM commodity ORDER BY date,hs_code", db_path=db_path)
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_country_df(db_path):
    if not os.path.exists(db_path): return pd.DataFrame()
    df = q("SELECT * FROM country ORDER BY date,country", db_path=db_path)
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_cxc_df(db_path, hs_code=None, country=None, date_from=None, date_to=None):
    if not os.path.exists(db_path): return pd.DataFrame()
    conds, params = [], []
    if hs_code:   conds.append("hs_code=?");   params.append(hs_code)
    if country:   conds.append("country=?");   params.append(country)
    if date_from: conds.append("date>=?");     params.append(date_from)
    if date_to:   conds.append("date<=?");     params.append(date_to)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    df = q(f"SELECT * FROM cxc {where} ORDER BY date,hs_code,export_usd_mn DESC",
           params=tuple(params), db_path=db_path)
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_db_stats(db_path):
    if not os.path.exists(db_path):
        return dict(commodity_rows=0, country_rows=0, cxc_rows=0,
                    hs_codes=0, countries=0, date_range="none")
    with conn(db_path) as c:
        cr  = c.execute("SELECT COUNT(*) FROM commodity").fetchone()[0]
        ctr = c.execute("SELECT COUNT(*) FROM country").fetchone()[0]
        cx  = c.execute("SELECT COUNT(*) FROM cxc").fetchone()[0]
        hs  = c.execute("SELECT COUNT(DISTINCT hs_code) FROM cxc").fetchone()[0]
        ct  = c.execute("SELECT COUNT(DISTINCT country) FROM cxc").fetchone()[0]
        dr  = c.execute("SELECT MIN(date)||' to '||MAX(date) FROM cxc").fetchone()[0]
    return dict(commodity_rows=cr, country_rows=ctr, cxc_rows=cx,
                hs_codes=hs, countries=ct, date_range=dr or "none")
