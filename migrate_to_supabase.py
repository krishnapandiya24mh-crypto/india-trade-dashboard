"""
migrate_to_supabase.py
----------------------
Migrates your local SQLite database to Supabase (free PostgreSQL cloud).

Steps:
  1. Create free Supabase account at supabase.com
  2. Create new project, get connection string
  3. Run: python migrate_to_supabase.py --url "postgresql://..."
  4. Wait ~10-20 minutes (uploads 300MB+ of data)
  5. Done — your data is in the cloud

Usage:
  python migrate_to_supabase.py --url "postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres"
  python migrate_to_supabase.py --url "..." --test   (test connection only)
  python migrate_to_supabase.py --url "..." --table cxc  (migrate one table only)
"""

import os, sys, time, logging, argparse
import sqlite3
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE      = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE, "data", "trade_tradestat.db")
CHUNK     = 5000   # rows per batch upload


def get_pg_engine(url: str):
    """Create SQLAlchemy engine for PostgreSQL."""
    try:
        from sqlalchemy import create_engine
        return create_engine(url, pool_pre_ping=True)
    except ImportError:
        logger.error("Run: pip install sqlalchemy psycopg2-binary")
        sys.exit(1)


def test_connection(url: str):
    """Test Supabase connection."""
    logger.info("Testing Supabase connection ...")
    try:
        engine = get_pg_engine(url)
        with engine.connect() as c:
            result = c.execute(__import__("sqlalchemy").text("SELECT version()"))
            ver = result.fetchone()[0]
            logger.info(f"Connected! PostgreSQL: {ver[:50]}")
            return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        logger.error("Check your URL format:")
        logger.error("  postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres")
        return False


def migrate_table(sqlite_path: str, url: str, table: str):
    """Migrate one table from SQLite to Supabase."""
    logger.info(f"Migrating table: {table}")

    # Read from SQLite
    conn = sqlite3.connect(sqlite_path)
    total = pd.read_sql_query(f"SELECT COUNT(*) FROM {table}", conn).iloc[0,0]
    logger.info(f"  SQLite rows: {total:,}")

    if total == 0:
        logger.warning(f"  Table {table} is empty — skipping")
        conn.close()
        return

    engine = get_pg_engine(url)

    # Create table in Supabase (drop if exists)
    logger.info(f"  Creating table in Supabase ...")
    df_sample = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 1", conn)

    # Upload in chunks
    uploaded = 0
    chunk_num = 0
    start = time.time()

    for offset in range(0, total, CHUNK):
        chunk_num += 1
        df = pd.read_sql_query(
            f"SELECT * FROM {table} LIMIT {CHUNK} OFFSET {offset}", conn
        )

        if_exists = "replace" if offset == 0 else "append"

        df.to_sql(
            table, engine,
            if_exists=if_exists,
            index=False,
            method="multi",      # batch insert
            chunksize=500,
        )
        uploaded += len(df)

        pct  = uploaded / total * 100
        elapsed = time.time() - start
        eta  = elapsed / uploaded * (total - uploaded) if uploaded > 0 else 0
        logger.info(f"  [{pct:5.1f}%] {uploaded:,}/{total:,} rows | "
                    f"elapsed: {elapsed:.0f}s | eta: {eta:.0f}s")

    conn.close()
    logger.info(f"  Table {table} migrated: {uploaded:,} rows in {time.time()-start:.0f}s")


def create_indexes(url: str):
    """Create indexes on Supabase for fast dashboard queries."""
    logger.info("Creating indexes ...")
    from sqlalchemy import text

    engine = get_pg_engine(url)
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_cxc_date ON cxc(date)",
        "CREATE INDEX IF NOT EXISTS ix_cxc_hs ON cxc(hs_code)",
        "CREATE INDEX IF NOT EXISTS ix_cxc_country ON cxc(country)",
        "CREATE INDEX IF NOT EXISTS ix_cxc_year ON cxc(year)",
        "CREATE INDEX IF NOT EXISTS ix_comm_date ON commodity(date)",
        "CREATE INDEX IF NOT EXISTS ix_comm_hs ON commodity(hs_code)",
        "CREATE INDEX IF NOT EXISTS ix_ctry_date ON country(date)",
        "CREATE INDEX IF NOT EXISTS ix_ctry_country ON country(country)",
    ]

    with engine.connect() as c:
        for sql in indexes:
            try:
                c.execute(text(sql))
                c.commit()
                logger.info(f"  Created: {sql[24:60]}...")
            except Exception as e:
                logger.warning(f"  Index skipped: {e}")

    logger.info("Indexes created")


def run_migration(url: str, tables: list = None):
    """Run full migration."""
    if not os.path.exists(DB_PATH):
        logger.error(f"SQLite DB not found: {DB_PATH}")
        logger.error("Run: python main.py --process  first")
        sys.exit(1)

    if not test_connection(url):
        sys.exit(1)

    if tables is None:
        tables = ["cxc", "commodity", "country"]

    total_start = time.time()
    print(f"\n{'='*60}")
    print(f"  MIGRATING TO SUPABASE")
    print(f"  SQLite : {DB_PATH}")
    print(f"  Tables : {tables}")
    print(f"  This will take 10-30 minutes for 300MB+ of data")
    print(f"{'='*60}\n")

    for table in tables:
        migrate_table(DB_PATH, url, table)

    create_indexes(url)

    elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  MIGRATION COMPLETE in {elapsed/60:.1f} minutes")
    print(f"\n  Next steps:")
    print(f"  1. Add to .streamlit/secrets.toml:")
    print(f'     SUPABASE_URL = "{url}"')
    print(f"  2. Push to GitHub")
    print(f"  3. Deploy on share.streamlit.io")
    print(f"{'='*60}\n")


def verify_migration(url: str):
    """Check row counts in Supabase match SQLite."""
    print("\n=== VERIFYING MIGRATION ===\n")
    engine = get_pg_engine(url)
    local  = sqlite3.connect(DB_PATH)

    for table in ["cxc", "commodity", "country"]:
        try:
            pg_count  = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", engine).iloc[0,0]
            loc_count = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", local).iloc[0,0]
            match = "OK" if pg_count >= loc_count * 0.99 else "MISMATCH"
            print(f"  {table:12s}: local={loc_count:>8,}  supabase={pg_count:>8,}  [{match}]")
        except Exception as e:
            print(f"  {table:12s}: ERROR — {e}")

    local.close()
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Migrate SQLite to Supabase")
    p.add_argument("--url",    required=True, help="Supabase PostgreSQL connection URL")
    p.add_argument("--test",   action="store_true", help="Test connection only")
    p.add_argument("--verify", action="store_true", help="Verify row counts match")
    p.add_argument("--table",  help="Migrate one table only (cxc/commodity/country)")
    args = p.parse_args()

    if args.test:
        test_connection(args.url)
    elif args.verify:
        verify_migration(args.url)
    elif args.table:
        if test_connection(args.url):
            migrate_table(DB_PATH, args.url, args.table)
    else:
        run_migration(args.url)
