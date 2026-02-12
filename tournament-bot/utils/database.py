import aiosqlite
import os
from config import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "database", "schema.sql")

async def init_db():
    os.makedirs(os.path.join(PROJECT_ROOT, "database"), exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            await db.executescript(f.read())
        await db.commit()
