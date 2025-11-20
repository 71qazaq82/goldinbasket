import sqlite3

conn = sqlite3.connect("attendance.db")
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
    work_duration TEXT,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
)
""")

conn.commit()
print("База данных успешно создана!")
