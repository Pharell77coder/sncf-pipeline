import os
from sqlalchemy import create_engine, URL

def engine():
    return create_engine(URL.create("postgresql+psycopg", username=os.getenv("PGUSER", "sncf"),
        password=os.environ["PGPASSWORD"], host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")), database=os.getenv("PGDATABASE", "sncf")), pool_pre_ping=True)
