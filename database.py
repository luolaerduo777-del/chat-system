import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        msg_type TEXT NOT NULL,
        time_str TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def create_user(username: str, password: str, created_at: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, password, created_at)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def create_room_if_not_exists(room_name: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rooms WHERE name = ?", (room_name,))
    room = cursor.fetchone()

    if room is None:
        cursor.execute(
            "INSERT INTO rooms (name, created_at) VALUES (?, ?)",
            (room_name, created_at)
        )
        conn.commit()

    conn.close()


def get_all_rooms():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM rooms ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row["name"] for row in rows]


def save_message(room_name: str, sender: str, text: str, msg_type: str, time_str: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (room_name, sender, text, msg_type, time_str, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (room_name, sender, text, msg_type, time_str, created_at))
    conn.commit()
    conn.close()


def get_recent_messages(room_name: str, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, text, msg_type, time_str
        FROM messages
        WHERE room_name = ?
        ORDER BY id DESC
        LIMIT ?
    """, (room_name, limit))
    rows = cursor.fetchall()
    conn.close()

    rows = list(rows)[::-1]
    return [
        {
            "sender": row["sender"],
            "text": row["text"],
            "type": row["msg_type"],
            "time": row["time_str"]
        }
        for row in rows
    ]