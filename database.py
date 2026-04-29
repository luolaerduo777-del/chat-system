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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS private_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        text TEXT NOT NULL,
        time_str TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_read INTEGER DEFAULT 0
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


def save_private_message(sender: str, receiver: str, text: str, time_str: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO private_messages (sender, receiver, text, time_str, created_at, is_read)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender, receiver, text, time_str, created_at, 0))

    conn.commit()
    conn.close()


def get_private_messages(user1: str, user2: str, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sender, receiver, text, time_str
        FROM private_messages
        WHERE 
            (sender = ? AND receiver = ?)
            OR
            (sender = ? AND receiver = ?)
        ORDER BY id DESC
        LIMIT ?
    """, (user1, user2, user2, user1, limit))

    rows = cursor.fetchall()
    conn.close()

    rows = list(rows)[::-1]

    return [
        {
            "type": "private",
            "sender": row["sender"],
            "to": row["receiver"],
            "text": row["text"],
            "time": row["time_str"]
        }
        for row in rows
    ]


def get_conversations(username: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM private_messages
        WHERE sender = ? OR receiver = ?
        ORDER BY id DESC
    """, (username, username))

    rows = cursor.fetchall()
    conn.close()

    seen = set()
    conversations = []

    for row in rows:
        other_user = row["receiver"] if row["sender"] == username else row["sender"]

        if other_user in seen:
            continue

        seen.add(other_user)

        conversations.append({
            "user": other_user,
            "last_text": row["text"],
            "last_sender": row["sender"],
            "time": row["time_str"]
        })

    return conversations