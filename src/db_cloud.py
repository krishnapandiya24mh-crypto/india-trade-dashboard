import os
from sqlalchemy import create_engine

def get_engine():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL not found")
    return create_engine(url)