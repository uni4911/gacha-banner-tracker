from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os
from src.db.models import Base, slugify

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "database.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

echo_sql = os.getenv("DB_ECHO", "false").lower() in ("true", "1")
engine = create_engine(DATABASE_URL, echo=echo_sql, connect_args={"check_same_thread": False})


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints, WAL mode, and busy timeout for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    # Safe auto-migration for existing SQLite database files
    with engine.connect() as conn:
        cursor = conn.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in cursor.fetchall()]
        if "slug" not in columns and "name" in columns:
            conn.execute(text("ALTER TABLE games ADD COLUMN slug VARCHAR(100)"))
            conn.commit()

        # Safe auto-migration for rewards.item_id
        cursor_rewards = conn.execute(text("PRAGMA table_info(rewards)"))
        reward_columns = [row[1] for row in cursor_rewards.fetchall()]
        if "item_id" not in reward_columns and "name" in reward_columns:
            conn.execute(text("ALTER TABLE rewards ADD COLUMN item_id INTEGER REFERENCES items(id)"))
            conn.commit()

        # Populate missing slugs for existing game rows
        games = conn.execute(text("SELECT id, name, slug FROM games")).fetchall()
        for g_id, g_name, g_slug in games:
            if not g_slug and g_name:
                computed = slugify(g_name)
                conn.execute(
                    text("UPDATE games SET slug = :slug WHERE id = :id"),
                    {"slug": computed, "id": g_id},
                )
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database was created / verified")