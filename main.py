from aiogram import Bot, Dispatcher, executor, types
import sqlite3
from datetime import datetime

TOKEN = "8187938139:AAFnnRe4PzH9l6Vke4uuRG1oaLtRhereXug"
ADMINS = [5209292400]

bot = Bot(TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()


def is_admin(uid):
    return uid in ADMINS


# ============================================
# /start
# ============================================
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    await msg.answer(
        "Привет 👋\n\n"
        "Чтобы зарегистрироваться: /reg Имя Код\n"
        "Чтобы начать/закончить смену — просто отправь свой код (только цифры)."
    )


# ============================================
# /myid
# ============================================
@dp.message_handler(commands=["myid"])
async def myid(msg: types.Message):
    await msg.answer(f"Ваш Telegram ID: {msg.from_user.id}")


# ============================================
# /test
# ============================================
@dp.message_handler(commands=["test"])
async def test_cmd(msg: types.Message):
    await msg.answer("🔥 Команда работает! Бот отвечает.")


# ============================================
# РЕГИСТРАЦИЯ СОТРУДНИКА
# ============================================
@dp.message_handler(commands=["reg"])
async def register(msg: types.Message):
    data = msg.text.split()

    if len(data) < 3:
        await msg.answer("Использование:\n/reg Имя Код")
        return

    name = data[1]
    code = data[2]

    try:
        cursor.execute("INSERT INTO employees (name, code) VALUES (?, ?)", (name, code))
        conn.commit()
        await msg.answer(f"Сотрудник добавлен:\nИмя: {name}\nКод: {code}")
    except:
        await msg.answer("❌ Такой код уже существует!")


# ======================================================
# ЛОВИМ ТОЛЬКО ЦИФРЫ — ЭТО КОД СОТРУДНИКА
# ======================================================
@dp.message_handler(lambda msg: msg.text.isdigit())
async def process_code(msg: types.Message):

    code = msg.text.strip()

    cursor.execute("SELECT id, name FROM employees WHERE code=?", (code,))
    emp = cursor.fetchone()

    if not emp:
        await msg.answer("❌ Неверный код сотрудника!")
        return

    emp_id, name = emp

    cursor.execute("""
        SELECT id, start_time
        FROM shifts
        WHERE employee_id=? AND end_time IS NULL
    """, (emp_id,))
    shift = cursor.fetchone()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Завершение смены
    if shift:
        shift_id, start_time = shift
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        diff = end_dt - start_dt

        hours = diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60
        dur = f"{hours}ч {mins}мин"

        cursor.execute("""
            UPDATE shifts SET end_time=?, work_duration=? WHERE id=?
        """, (now, dur, shift_id))
        conn.commit()

        await msg.answer(f"🟥 {name}, смена завершена!\n⏳ {dur}")

        for admin_id in ADMINS:
            await bot.send_message(admin_id, f"🟥 {name} завершил смену!\n⏳ {dur}")

        return

    # Начало смены
    cursor.execute("""
        INSERT INTO shifts (employee_id, start_time)
        VALUES (?, ?)
    """, (emp_id, now))
    conn.commit()

    await msg.answer(f"🟩 {name}, смена началась!\n🕒 {now}")

    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"🟩 {name} начал смену!\n🕒 {now}")


# ======================================================
# /admin — ПАНЕЛЬ
# ======================================================
@dp.message_handler(commands=["admin"])
async def admin_panel(msg: types.Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа")
        return

    cursor.execute("SELECT name, code FROM employees")
    emps = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM shifts")
    shift_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT employees.name, shifts.start_time
        FROM shifts
        JOIN employees ON employees.id = shifts.employee_id
        WHERE shifts.end_time IS NULL
    """)
    active = cursor.fetchall()

    text = "<b>📊 АДМИН-ПАНЕЛЬ</b>\n\n"
    text += f"👥 Сотрудников: {len(emps)}\n"
    text += f"📂 Всего смен: {shift_count}\n\n"

    text += "🟩 <b>Сейчас работают:</b>\n"
    if not active:
        text += "Никто\n"
    else:
        for name, st in active:
            text += f"— {name} c {st}\n"

    text += "\n👥 <b>Сотрудники:</b>\n"
    for name, code in emps:
        text += f"{name} — {code}\n"

    await msg.answer(text, parse_mode="HTML")


@dp.message_handler(commands=["delete"])
async def delete_employee(msg: types.Message):
    # проверяем права
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ У вас нет доступа.")
        return

    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование:\n/delete код_сотрудника\nПример:\n/delete 1234")
        return

    code = parts[1]

    # проверяем сотрудника
    cursor.execute("SELECT id, name FROM employees WHERE code=?", (code,))
    emp = cursor.fetchone()

    if not emp:
        await msg.answer("❌ Сотрудник с таким кодом не найден.")
        return

    emp_id, name = emp

    # удаляем смены
    cursor.execute("DELETE FROM shifts WHERE employee_id=?", (emp_id,))
    # удаляем сотрудника
    cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()

    await msg.answer(f"🗑 Сотрудник <b>{name}</b> (код {code}) успешно удалён.", parse_mode="HTML")


# ======================================================
# /admin_today
# ======================================================
@dp.message_handler(commands=["admin_today"])
async def admin_today(msg: types.Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа")
        return

    cursor.execute("""
        SELECT employees.name, shifts.start_time, shifts.end_time, shifts.work_duration
        FROM shifts
        JOIN employees ON employees.id = shifts.employee_id
        WHERE DATE(shifts.start_time) = DATE('now')
    """)
    rows = cursor.fetchall()

    if not rows:
        await msg.answer("Сегодня никто не работал.")
        return

    text = "<b>📅 Смены за сегодня</b>\n\n"
    for name, st, en, wd in rows:
        text += f"👤 {name}\n"
        text += f"Старт: {st}\n"
        text += f"Конец: {en if en else 'идёт'}\n"
        text += f"Отработано: {wd if wd else '-'}\n\n"

    await msg.answer(text, parse_mode="HTML")


# ======================================================
# /info код
# ======================================================
@dp.message_handler(commands=["info"])
async def info_cmd(msg: types.Message):

    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа")
        return

    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /info код")
        return

    code = parts[1]

    cursor.execute("SELECT id, name FROM employees WHERE code=?", (code,))
    emp = cursor.fetchone()

    if not emp:
        await msg.answer("Сотрудник не найден")
        return

    emp_id, name = emp

    cursor.execute("SELECT work_duration FROM shifts WHERE employee_id=?", (emp_id,))
    rows = cursor.fetchall()

    total = 0
    for (wd,) in rows:
        if wd:
            h, m = wd.replace("ч", "").replace("мин", "").split()
            total += int(h) * 60 + int(m)

    total_h = total // 60
    total_m = total % 60

    cursor.execute("""
        SELECT start_time FROM shifts
        WHERE employee_id=? AND end_time IS NULL
    """, (emp_id,))
    active = cursor.fetchone()

    text = (
        "<b>📄 Информация о сотруднике</b>\n\n"
        f"Имя: {name}\n"
        f"Код: {code}\n\n"
        f"Всего отработано: {total_h}ч {total_m}мин\n\n"
    )

    if active:
        text += f"🟩 Сейчас работает\nСтарт: {active[0]}\n"

    await msg.answer(text, parse_mode="HTML")


# ======================================================
# СТАРТ
# ======================================================
executor.start_polling(dp)
