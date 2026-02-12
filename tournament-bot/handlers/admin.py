from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from config import ADMIN_IDS, DB_PATH, DEFAULT_REQUISITES
from states.create_tournament import CreateTournament

router = Router()

def is_admin(user_id):
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Админ панель:\n"
        "/create - создать турнир\n"
        "/finish - завершить турнир\n"
        "/ban ID - забанить игрока"
    )

@router.message(Command("create"))
async def create_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(CreateTournament.title)
    await message.answer("Название турнира:")

@router.message(CreateTournament.title)
async def set_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(CreateTournament.max_players)
    await message.answer("Количество мест:")

@router.message(CreateTournament.max_players)
async def set_players(message: types.Message, state: FSMContext):
    await state.update_data(max_players=int(message.text))
    await state.set_state(CreateTournament.entry_fee)
    await message.answer("Взнос (₽):")

@router.message(CreateTournament.entry_fee)
async def set_fee(message: types.Message, state: FSMContext):
    await state.update_data(entry_fee=int(message.text))
    await state.set_state(CreateTournament.prize_places)
    await message.answer("Количество призовых мест:")

@router.message(CreateTournament.prize_places)
async def set_places(message: types.Message, state: FSMContext):
    await state.update_data(prize_places=int(message.text))
    await state.set_state(CreateTournament.prizes)
    await message.answer("Введите суммы призов через запятую:")

@router.message(CreateTournament.prizes)
async def finish_create(message: types.Message, state: FSMContext):
    data = await state.get_data()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO tournaments
            (title, max_players, entry_fee, prize_places, prizes, requisites, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["title"],
            data["max_players"],
            data["entry_fee"],
            data["prize_places"],
            message.text,
            DEFAULT_REQUISITES,
            "registration_open"
        ))
        await db.commit()

    await state.clear()
    await message.answer("Турнир создан ✅")

@router.message(Command("finish"))
async def finish_tournament(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tournaments SET status='finished'")
        await db.commit()

    await message.answer("Турнир завершён ✅")

@router.message(Command("ban"))
async def ban_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        return

    user_id = int(parts[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned=1 WHERE user_id=?",
            (user_id,)
        )
        await db.commit()

    await message.answer("Игрок забанен 🚫")   

from aiogram.filters import Command

# --------------------------
# Завершение турнира + уведомления
# --------------------------
@router.message(Command("finish"))
async def finish_tournament(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Отмечаем турнир как завершённый
        await db.execute("UPDATE tournaments SET status='finished' WHERE status='registration_open'")
        await db.commit()

        # Получаем всех участников завершенного турнира
        async with db.execute("""
            SELECT user_id FROM participants
            WHERE payment_status='approved'
        """) as cur:
            participants = await cur.fetchall()

    # Отправляем уведомление каждому участнику
    for user in participants:
        try:
            await message.bot.send_message(
                user[0],
                "Турнир завершен! Выберите результат:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🏆 Я выиграл", callback_data="win"),
                        InlineKeyboardButton(text="❌ Я проиграл", callback_data="lose")
                    ]
                ])
            )
        except:
            # Игнорируем ошибки, если бот не может написать
            pass

    await message.answer("Турнир завершен, уведомления отправлены ✅")

# --------------------------
# Очистка участников завершенного турнира (для админа)
# --------------------------
@router.message(Command("clear_participants"))
async def clear_participants(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM participants WHERE result_status IN ('paid', 'lost', 'rejected')")
        await db.commit()

    await message.answer("Участники завершенных турниров очищены из базы ✅")

