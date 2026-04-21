from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 房间聊天记录
room_messages = {}

# 房间在线用户
room_users = {}

# 每个连接对应的用户信息
# 结构:
# {
#   sid: {"username": "A", "room": "math"}
# }
user_sessions = {}


def now_time():
    return datetime.now().strftime('%H:%M')


def trim_room_messages(room, limit=100):
    if room in room_messages and len(room_messages[room]) > limit:
        room_messages[room] = room_messages[room][-limit:]


def build_system_message(text):
    return {
        'type': 'system',
        'sender': '系统',
        'text': text,
        'time': now_time()
    }


def broadcast_user_list(room):
    if room not in room_users:
        room_users[room] = []
    socketio.emit('user_list', room_users[room], to=room)


@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@socketio.on('join')
def handle_join(data):
    username = data.get('username', '').strip()
    room = data.get('room', '').strip()
    sid = request.sid

    if not username or not room:
        emit('error_message', '用户名和房间名不能为空')
        return

    # 如果当前连接已经在别的房间，先退出旧房间
    if sid in user_sessions:
        old_username = user_sessions[sid]['username']
        old_room = user_sessions[sid]['room']

        if old_room != room or old_username != username:
            leave_room(old_room)

            if old_room in room_users and old_username in room_users[old_room]:
                room_users[old_room].remove(old_username)

            leave_message = build_system_message(f'{old_username} 离开了房间 {old_room}')
            if old_room not in room_messages:
                room_messages[old_room] = []
            room_messages[old_room].append(leave_message)
            trim_room_messages(old_room)

            socketio.emit('message', leave_message, to=old_room)
            broadcast_user_list(old_room)

    join_room(room)

    if room not in room_messages:
        room_messages[room] = []

    if room not in room_users:
        room_users[room] = []

    if username not in room_users[room]:
        room_users[room].append(username)

    user_sessions[sid] = {
        'username': username,
        'room': room
    }

    # 先把历史消息发给当前用户
    emit('history', room_messages[room])

    # 再广播进入消息
    join_message = build_system_message(f'{username} 进入了房间 {room}')
    room_messages[room].append(join_message)
    trim_room_messages(room)

    socketio.emit('message', join_message, to=room)

    # 广播在线用户列表
    broadcast_user_list(room)


@socketio.on('message')
def handle_message(data):
    username = data.get('username', '').strip()
    room = data.get('room', '').strip()
    msg = data.get('msg', '').strip()

    if not username or not room or not msg:
        return

    if room not in room_messages:
        room_messages[room] = []

    message_data = {
        'type': 'user',
        'sender': username,
        'text': msg,
        'time': now_time()
    }

    room_messages[room].append(message_data)
    trim_room_messages(room)

    socketio.emit('message', message_data, to=room)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid

    if sid not in user_sessions:
        return

    username = user_sessions[sid]['username']
    room = user_sessions[sid]['room']

    if room not in room_messages:
        room_messages[room] = []

    if room in room_users and username in room_users[room]:
        room_users[room].remove(username)

    leave_message = build_system_message(f'{username} 离开了房间 {room}')
    room_messages[room].append(leave_message)
    trim_room_messages(room)

    socketio.emit('message', leave_message, to=room)
    broadcast_user_list(room)

    del user_sessions[sid]


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)