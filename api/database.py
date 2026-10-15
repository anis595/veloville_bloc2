import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

RACINE = Path(__file__).resolve().parents[1]
load_dotenv(RACINE / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://veloville:veloville@localhost:5432/veloville")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
