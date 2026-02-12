from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from states.registration import Registration
from states.result_submission import ResultSubmission
from config import DB_PATH, ADMIN_IDS, DEFAULT_REQUISITES
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from aiogram.filters import Text

router = Router()

# --------------------------
# Клавиатуры
# --------------------------
def payment_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"pay_ok:{user_id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"pay_no:{user_id}")
        ]
    ])

def result_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Я выиграл", callback_data="win"),
            InlineKeyboardButton(text="❌ Я проиграл", callback_data="lose")
        ]
    ])

# --------------------------
# Показ турниров и регистрация
# --------------------------
@router.message(lambda m: m.text.lower() == "турниры")
async def show_tournaments(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title FROM tournaments WHERE status='registration_open'") as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("Нет активных турниров")
        return

    text = "\n".join([f"{r[0]}. {r[1]}" for r in rows])
    await message.answer(f"Доступные турниры:\n{text}\nВведите ID турнира для регистрации:")

@router.message(lambda m: m.text.isdigit())
async def register_start(message: types.Message, state: FSMContext):
    await state.update_data(tournament_id=int(message.text))
    await state.set_state(Registration.nickname)
    await message.answer("Введите игровой ник:")

@router.message(Registration.nickname)
async def save_nickname(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tournament_id = data["tournament_id"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO participants (tournament_id, user_id, username, nickname, payment_status, result_status, requisites)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tournament_id,
            message.from_user.id,
            message.from_user.username,
            message.text,
            "pending",
            "none",
            DEFAULT_REQUISITES
        ))
        await db.commit()

    await message.answer(f"Оплатите по реквизитам:\n\n{DEFAULT_REQUISITES}\n\n"
                         "После оплаты отправьте скрин оплаты в этот чат.")

# --------------------------
# Получение скрина оплаты
# --------------------------
@router.message(F.photo)
async def payment_screenshot(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT nickname, username FROM participants WHERE user_id=?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            if not row:
                await message.answer("Вы не зарегистрированы в турнире!")
                return
            nickname, username = row

        await db.execute("""
            UPDATE participants SET payment_status='pending' WHERE user_id=?
        """, (message.from_user.id,))
        await db.commit()

    # Отправляем админу
    for admin in ADMIN_IDS:
        await message.bot.send_photo(
            admin,
            message.photo[-1].file_id,
            caption=f"Новая оплата\nID: {message.from_user.id}\nUsername: @{username}\nИгровой ник: {nickname}",
            reply_markup=payment_keyboard(message.from_user.id)
        )

    await message.answer("Скрин отправлен администратору. Ожидайте подтверждения ✅")

# --------------------------
# Обработка кнопок оплаты
# --------------------------
@router.callback_query(Text(startswith="pay_ok"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE participants SET payment_status='approved' WHERE user_id=?", (user_id,))
        await db.commit()

    await callback.message.edit_caption("Оплата подтверждена ✅")
    await callback.bot.send_message(user_id, "Ваша оплата подтверждена ✅")
    await callback.answer()

@router.callback_query(Text(startswith="pay_no"))
async def reject_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE participants SET payment_status='rejected' WHERE user_id=?", (user_id,))
        await db.commit()

    await callback.message.edit_caption("Оплата отклонена ❌")
    await callback.bot.send_message(user_id, "Ваша оплата отклонена администратором ❌")
    await callback.answer()

# --------------------------
# Кнопки результата после завершения турнира
# --------------------------
@router.message(F.text.lower() == "результат")
async def send_result_keyboard(message: types.Message):
    await message.answer("Выберите результат:", reply_markup=result_keyboard())

@router.callback_query(Text("lose"))
async def lose(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE participants SET result_status='lost' WHERE user_id=?", (callback.from_user.id,))
        await db.commit()
    await callback.message.answer("Результат зафиксирован ❌")
    await callback.answer()

@router.callback_query(Text("win"))
async def win(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправьте скрин победы, реквизиты для выплаты и занятое место в одном сообщении.\n"
        "Формат:\nМесто: 1\nРеквизиты: Сбербанк 2202208214031917 Завкиддин А."
    )
    await state.set_state(ResultSubmission.screenshot)

# --------------------------
# FSM победы и выплата
# --------------------------
@router.message(ResultSubmission.screenshot, F.photo)
async def process_win_submission(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте скрин победы (фото).")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT nickname, username FROM participants WHERE user_id=?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            if not row:
                await message.answer("Вы не зарегистрированы!")
                return
            nickname, username = row

    await state.update_data(
        screenshot_id=message.photo[-1].file_id,
        caption=message.text
    )

    for admin in ADMIN_IDS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выплачено", callback_data=f"paid_ok:{message.from_user.id}"),
                InlineKeyboardButton(text="❌ Отказать", callback_data=f"paid_no:{message.from_user.id}")
            ]
        ])
        await message.bot.send_photo(
            chat_id=admin,
            photo=message.photo[-1].file_id,
            caption=f"Победа!\nID: {message.from_user.id}\nUsername: @{username}\nИгровой ник: {nickname}\n\n{message.text}",
            reply_markup=keyboard
        )

    await state.clear()
    await message.answer("Ваш результат отправлен администратору ✅")

@router.callback_query(Text(startswith="paid_ok"))
async def confirm_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE participants SET result_status='paid' WHERE user_id=?", (user_id,))
        await db.commit()

    await callback.message.edit_caption("Выплата подтверждена ✅")
    await callback.bot.send_message(user_id, "Ваша победа подтверждена и выплата произведена ✅")
    await callback.answer()

@router.callback_query(Text(startswith="paid_no"))
async def reject_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE participants SET result_status='rejected' WHERE user_id=?", (user_id,))
        await db.commit()

    await callback.message.edit_caption("Выплата отклонена ❌")
    await callback.bot.send_message(user_id, "Ваша победа отклонена администратором ❌")
    await callback.answer()
