# app.py（刷新页面强制重新登录版）

把你现在的 app.py 全部删除，然后用下面这个完整文件覆盖。

```python
import os
import uuid
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
    save_private_message,
    get_private_messages,
    mark_private_messages_read,
    get_conversations,
)
from ai_service import stream_ai

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=None)
app.secret_key = "chat-system-secret-key-change-me"

# 🔥 刷新后强制重新登录
app.config["SESSION_PERMANENT"] = False

socketio = SocketIO(app, cors_allowed_origins="*")

room_users = {}
user_sessions = {}
user_sid_map = {}
DEFAULT_ROOMS = []


def now_display_time():
    return datetime.now().strftime("%H:%M")


def now_full_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_username():
    return session.get("username")


def is_logged_in():
    return "username" in session


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


# 🔥 每次刷新页面都会重新登录
@app.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"ok": False, "message": "未登录"}), 401

    username = session["username"]

    # 关键：返回用户名后立刻清 session
    session.clear()

    return jsonify({
        "ok": True,
        "username": username
    })


@app.route("/api/conversations")
def api_conversations():
    username = current_username()

    if not username:
        return jsonify({"ok": False, "message": "未登录"}), 401

    conversations = get_conversations(username)

    return jsonify({
        "ok": True,
        "conversations": conversations
    })


@socketio.on("disconnect")
def handle_disconnect():
    pass


init_database()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
```

注意：

```text
这是“极端强制重新登录模式”
```

刷新页面就会退出登录。

包括：

```text
F5
Ctrl+R
重新打开页面
```

都会重新登录。
