import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE shifts ADD COLUMN work_duration TEXT")
    print("✔ Колонка work_duration добавлена!")
except Exception as e:
    print("Уже существует или ошибка:", e)

conn.commit()
conn.close()
