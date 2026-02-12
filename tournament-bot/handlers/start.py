from aiogram import Router, types
from aiogram.filters import CommandStart
import aiosqlite
from config import DB_PATH

router = Router()

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (message.from_user.id, message.from_user.username)
        )
        await db.commit()

    await message.answer("Добро пожаловать в турнирный бот!\nНажмите 'Турниры' чтобы зарегистрироваться")
