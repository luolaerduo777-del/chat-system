import os
import psycopg2
import psycopg2.extras


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("未配置 DATABASE_URL，请在 Render 环境变量中添加 PostgreSQL Internal URL")

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        text TEXT NOT NULL,
        time_str TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_read INTEGER DEFAULT 0
    )
    """)

    # 兼容旧数据库：如果之前建表时没有 is_read，这里自动补上。
    cursor.execute("""
        ALTER TABLE private_messages
        ADD COLUMN IF NOT EXISTS is_read INTEGER DEFAULT 0
    """)

    # 提升会话列表、历史记录、未读统计查询速度。
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_private_messages_users_id
        ON private_messages (sender, receiver, id DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_private_messages_unread
        ON private_messages (receiver, sender, is_read)
    """)

    conn.commit()
    cursor.close()
    conn.close()


def create_user(username: str, password: str, created_at: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password, created_at) VALUES (%s, %s, %s)",
            (username, password, created_at)
        )
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def get_user_by_username(username: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()
    return user


def create_room_if_not_exists(room_name: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO rooms (name, created_at)
        VALUES (%s, %s)
        ON CONFLICT (name) DO NOTHING
    """, (room_name, created_at))

    conn.commit()
    cursor.close()
    conn.close()


def get_all_rooms():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM rooms ORDER BY id DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [row["name"] for row in rows]


def save_message(room_name: str, sender: str, text: str, msg_type: str, time_str: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages (room_name, sender, text, msg_type, time_str, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (room_name, sender, text, msg_type, time_str, created_at))

    conn.commit()
    cursor.close()
    conn.close()


def get_recent_messages(room_name: str, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sender, text, msg_type, time_str
        FROM messages
        WHERE room_name = %s
        ORDER BY id DESC
        LIMIT %s
    """, (room_name, limit))

    rows = cursor.fetchall()

    cursor.close()
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
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sender, receiver, text, time_str, created_at, 0))

    conn.commit()
    cursor.close()
    conn.close()


def get_private_messages(user1: str, user2: str, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sender, receiver, text, time_str, is_read
        FROM private_messages
        WHERE 
            (sender = %s AND receiver = %s)
            OR
            (sender = %s AND receiver = %s)
        ORDER BY id DESC
        LIMIT %s
    """, (user1, user2, user2, user1, limit))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    rows = list(rows)[::-1]

    return [
        {
            "type": "private",
            "sender": row["sender"],
            "to": row["receiver"],
            "text": row["text"],
            "time": row["time_str"],
            "is_read": row["is_read"]
        }
        for row in rows
    ]


def mark_private_messages_read(reader: str, other_user: str):
    """把 other_user 发给 reader 的未读私聊全部标记为已读。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE private_messages
        SET is_read = 1
        WHERE sender = %s
          AND receiver = %s
          AND is_read = 0
    """, (other_user, reader))

    conn.commit()
    cursor.close()
    conn.close()


def get_conversations(username: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM private_messages
        WHERE sender = %s OR receiver = %s
        ORDER BY id DESC
    """, (username, username))

    rows = cursor.fetchall()

    cursor.execute("""
        SELECT sender, COUNT(*) AS unread_count
        FROM private_messages
        WHERE receiver = %s AND is_read = 0
        GROUP BY sender
    """, (username,))

    unread_rows = cursor.fetchall()

    cursor.close()
    conn.close()

    unread_map = {
        row["sender"]: int(row["unread_count"])
        for row in unread_rows
    }

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
            "time": row["time_str"],
            "unread_count": unread_map.get(other_user, 0)
        })

    return conversations
