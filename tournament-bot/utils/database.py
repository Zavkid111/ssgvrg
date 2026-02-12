import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        with open("database/schema.sql", "r", encoding="utf-8") as f:
            await db.executescript(f.read())
        await db.commit()
