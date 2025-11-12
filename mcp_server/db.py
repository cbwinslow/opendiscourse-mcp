"""Database helpers: SQLAlchemy engine and connection helpers."""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
import os
from typing import Optional


_engine: Optional[Engine] = None


def get_sqlalchemy_engine(database_url: Optional[str] = None) -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    # echo can be controlled via env var in future
    _engine = create_engine(database_url, future=True)
    return _engine


def get_raw_connection(database_url: Optional[str] = None):
    # convenience: return a raw DBAPI connection using SQLAlchemy engine
    eng = get_sqlalchemy_engine(database_url=database_url)
    return eng.raw_connection()
