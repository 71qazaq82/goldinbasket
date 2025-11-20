import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.enums.parse_mode import ParseMode
from aiogram import F

TOKEN = os.getenv("TOKEN")
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",")]

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    code TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    start_time TEXT,
    end_time TEXT,
    work_duration TEXT
)
""")
conn.commit()


@router.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Введите ваш код, чтобы начать или завершить смену.\n"
                     "Если вы новый сотрудник — отправьте команду /register")


@router.message(Command("register"))
async def register(msg: types.Message):
    await msg.answer("Введите ваше имя:")
    dp["register_step"] = {"user_id": msg.from_user.id, "step": "name"}


@router.message(F.text)
async def register_steps(msg: types.Message):
    state = dp.get("register_step")

    if state and state["user_id"] == msg.from_user.id:
        if state["step"] == "name":
            dp["register_step"]["name"] = msg.text
            dp["register_step"]["step"] = "code"
            await msg.answer("Введите уникальный код сотрудника:")
            return

        if state["step"] == "code":
            name = dp["register_step"]["name"]
            code = msg.text.strip()

            cursor.execute("SELECT id FROM employees WHERE code=?", (code,))
            if cursor.fetchone():
                await msg.answer("❌ Такой код уже существует. Попробуйте другой.")
                return

            cursor.execute("INSERT INTO employees (name, code) VALUES (?, ?)", (name, code))
            conn.commit()

            dp["register_step"] = None
            await msg.answer(f"🟩 Сотрудник <b>{name}</b> добавлен!")
            return

    # Если это не регистрация — обработка смен:
    code = msg.text.strip()
    cursor.execute("SELECT id, name FROM employees WHERE code=?", (code,))
    employee = cursor.fetchone()

    if not employee:
        return await msg.answer("❌ Неверный код сотрудника.")

    employee_id, name = employee

    cursor.execute("SELECT id, start_time FROM shifts WHERE employee_id=? AND end_time IS NULL",
                   (employee_id,))
    open_shift = cursor.fetchone()

    if open_shift:
        shift_id, start_time = open_shift

        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.now()

        work_duration = str(end_dt - start_dt).split(".")[0]

        cursor.execute("""
        UPDATE shifts SET end_time=?, work_duration=? WHERE id=?
        """, (end_dt.isoformat(), work_duration, shift_id))
        conn.commit()

        return await msg.answer(f"🟥 Смена завершена!\n⏳ Отработано: <b>{work_duration}</b>")

    else:
        cursor.execute("""
        INSERT INTO shifts (employee_id, start_time)
        VALUES (?, ?)
        """, (employee_id, datetime.now().isoformat()))
        conn.commit()

        return await msg.answer(f"🟩 Смена начата для <b>{name}</b>!")


@router.message(Command("admin"))
async def admin_panel(msg: types.Message):
    if msg.from_user.id not in ADMINS:
        return await msg.answer("⛔ У вас нет доступа.")

    cursor.execute("""
    SELECT shifts.id, employees.name, shifts.start_time, shifts.end_time, shifts.work_duration
    FROM shifts
    JOIN employees ON employees.id = shifts.employee_id
    ORDER BY shifts.id DESC
    """)

    rows = cursor.fetchall()

    if not rows:
        return await msg.answer("Нет данных о сменах.")

    text = "<b>Все смены:</b>\n\n"

    for row in rows[:20]:
        shift_id, name, start, end, duration = row
        text += (
            f"👤 <b>{name}</b>\n"
            f"⏱ Начало: {start}\n"
            f"🏁 Конец: {end}\n"
            f"⏳ Длительность: {duration}\n"
            "--------\n"
        )

    await msg.answer(text)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
