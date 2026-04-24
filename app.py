import os
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, session, redirect, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

from database import (
    init_database,
    create_user,
    get_user_by_username,
    create_room_if_not_exists,
    get_all_rooms,
    save_message,
    get_recent_messages,
)
from ai_service import ask_ai

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=None)
app.secret_key = "chat-system-secret-key-change-me"
socketio = SocketIO(app, cors_allowed_origins="*")

room_users = {}
user_sessions = {}

DEFAULT_ROOMS = []


def now_display_time() -> str:
    return datetime.now().strftime("%H:%M")


def now_full_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_username():
    return session.get("username")


def is_logged_in() -> bool:
    return "username" in session


def build_system_message(text: str):
    return {
        "type": "system",
        "sender": "系统",
        "text": text,
        "time": now_display_time()
    }


def build_user_message(sender: str, text: str, msg_type: str = "user"):
    return {
        "type": msg_type,
        "sender": sender,
        "text": text,
        "time": now_display_time()
    }


def broadcast_user_list(room_name: str):
    users = room_users.get(room_name, [])
    socketio.emit("user_list", users, to=room_name)


@app.route("/")
def root():
    if is_logged_in():
        return send_from_directory(BASE_DIR, "index.html")
    return redirect("/login")


@app.route("/login")
def login_page():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/register")
def register_page():
    return send_from_directory(BASE_DIR, "register.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({"ok": False, "message": "用户名和密码不能为空"}), 400

    if len(username) < 2:
        return jsonify({"ok": False, "message": "用户名至少2位"}), 400

    if len(password) < 4:
        return jsonify({"ok": False, "message": "密码至少4位"}), 400

    success = create_user(username, password, now_full_time())
    if not success:
        return jsonify({"ok": False, "message": "用户名已存在"}), 400

    return jsonify({"ok": True, "message": "注册成功"})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    user = get_user_by_username(username)
    if user is None or user["password"] != password:
        return jsonify({"ok": False, "message": "用户名或密码错误"}), 400

    session["username"] = username
    return jsonify({"ok": True, "message": "登录成功"})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"ok": False, "message": "未登录"}), 401
    return jsonify({"ok": True, "username": session["username"]})


@app.route("/api/rooms")
def api_rooms():
    db_rooms = get_all_rooms()
    room_list = list(dict.fromkeys(DEFAULT_ROOMS + db_rooms))
    return jsonify({"ok": True, "rooms": room_list})


@socketio.on("join")
def handle_join(data):
    username = current_username()
    room_name = str((data or {}).get("room", "")).strip()
    sid = request.sid

    if not username:
        emit("error_message", "请先登录")
        return

    if not room_name:
        emit("error_message", "房间名不能为空")
        return

    create_room_if_not_exists(room_name, now_full_time())

    if sid in user_sessions:
        old_username = user_sessions[sid]["username"]
        old_room = user_sessions[sid]["room"]

        if old_room:
            leave_room(old_room)

            if old_room in room_users and old_username in room_users[old_room]:
                room_users[old_room].remove(old_username)

                leave_message = build_system_message(f"{old_username} 离开了房间 {old_room}")
                save_message(
                    old_room,
                    leave_message["sender"],
                    leave_message["text"],
                    leave_message["type"],
                    leave_message["time"],
                    now_full_time()
                )
                socketio.emit("message", leave_message, to=old_room)
                broadcast_user_list(old_room)

    join_room(room_name)

    if room_name not in room_users:
        room_users[room_name] = []

    if username not in room_users[room_name]:
        room_users[room_name].append(username)

    user_sessions[sid] = {
        "username": username,
        "room": room_name
    }

    history = get_recent_messages(room_name, limit=100)
    emit("history", history)

    join_message = build_system_message(f"{username} 进入了房间 {room_name}")
    save_message(
        room_name,
        join_message["sender"],
        join_message["text"],
        join_message["type"],
        join_message["time"],
        now_full_time()
    )

    socketio.emit("message", join_message, to=room_name)
    broadcast_user_list(room_name)


@socketio.on("message")
def handle_message(data):
    username = current_username()
    room_name = str((data or {}).get("room", "")).strip()
    msg = str((data or {}).get("msg", "")).strip()
    ai_enabled = bool((data or {}).get("ai_enabled", False))

    if not username:
        emit("error_message", "请先登录")
        return

    if not room_name or not msg:
        return

    # 用户消息
    user_message = build_user_message(username, msg, "user")
    save_message(
        room_name,
        user_message["sender"],
        user_message["text"],
        user_message["type"],
        user_message["time"],
        now_full_time()
    )
    socketio.emit("message", user_message, to=room_name)

    # ================= AI逻辑 =================
    if ai_enabled and msg.lower().startswith("@ai"):
        ai_question = msg[3:].strip()

        if not ai_question:
            ai_text = "你可以这样用我：@ai 什么是API？ / @ai 总结 / @ai 笔记 / @ai 老师 解释一下WebSocket"
        else:
            mode = "default"

            # 获取上下文
            recent_messages = get_recent_messages(room_name, limit=30)
            context_lines = []

            for item in recent_messages:
                if item.get("type") != "system":
                    context_lines.append(f"{item['sender']}: {item['text']}")

            context = "\n".join(context_lines)

            # 模式判断
            if ai_question.startswith("总结"):
                mode = "summary"
                ai_question = "请总结这个房间最近的聊天内容。"

            elif ai_question.startswith("笔记"):
                mode = "notes"
                ai_question = "请生成学习笔记。"

            elif ai_question.startswith("老师"):
                mode = "teacher"
                ai_question = ai_question.replace("老师", "", 1).strip()

            elif ai_question.startswith("学长"):
                mode = "senior"
                ai_question = ai_question.replace("学长", "", 1).strip()

            elif ai_question.startswith("吐槽"):
                mode = "funny"
                ai_question = ai_question.replace("吐槽", "", 1).strip()

            ai_text = ask_ai(ai_question, mode=mode, context=context)

        # AI回复
        ai_message = build_user_message("AI助手", ai_text, "ai")
        save_message(
            room_name,
            ai_message["sender"],
            ai_message["text"],
            ai_message["type"],
            ai_message["time"],
            now_full_time()
        )
        socketio.emit("message", ai_message, to=room_name)

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    if sid not in user_sessions:
        return

    username = user_sessions[sid]["username"]
    room_name = user_sessions[sid]["room"]

    if room_name in room_users and username in room_users[room_name]:
        room_users[room_name].remove(username)

    leave_message = build_system_message(f"{username} 离开了房间 {room_name}")
    save_message(
        room_name,
        leave_message["sender"],
        leave_message["text"],
        leave_message["type"],
        leave_message["time"],
        now_full_time()
    )

    socketio.emit("message", leave_message, to=room_name)
    broadcast_user_list(room_name)

    del user_sessions[sid]


if __name__ == "__main__":
    init_database()
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)