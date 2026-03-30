import os
import pandas as pd
from sqlalchemy import create_engine

def get_engine():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL not found")
    return create_engine(url)

# run query
def q(query):
    engine = get_engine()
    return pd.read_sql(query, engine)

# basic stats (you can customize later)
def get_stats():
    engine = get_engine()
    try:
        df = pd.read_sql("SELECT COUNT(*) as total_rows FROM cxc", engine)
        return df
    except:
        return None

# check if cloud
def is_cloud():
    return True