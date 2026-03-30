import os
import pandas as pd
from sqlalchemy import create_engine

# create engine
def get_engine():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL not found")
    return create_engine(url)

# query function
def q(query):
    engine = get_engine()
    return pd.read_sql(query, engine)

# stats function
def get_stats():
    engine = get_engine()
    try:
        return pd.read_sql("SELECT COUNT(*) as total FROM cxc", engine)
    except Exception as e:
        return None

# cloud check
def is_cloud():
    return True