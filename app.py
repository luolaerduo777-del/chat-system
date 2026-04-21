from flask import Flask, send_from_directory
from flask_socketio import SocketIO, join_room, emit
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储每个房间的聊天记录
# 结构示例：
# {
#     "math": [
#         {"type": "user", "sender": "A", "text": "你好", "time": "14:23"},
#         {"type": "system", "sender": "系统", "text": "B 进入了房间 math", "time": "14:24"}
#     ]
# }
room_messages = {}


@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']

    join_room(room)

    if room not in room_messages:
        room_messages[room] = []

    # 先把这个房间已有聊天记录发给当前用户
    emit('history', room_messages[room])

    # 再广播系统消息给房间内所有人
    system_message = {
        'type': 'system',
        'sender': '系统',
        'text': f'{username} 进入了房间 {room}',
        'time': datetime.now().strftime('%H:%M')
    }

    # 系统消息也存进去，这样刷新后还能看到
    room_messages[room].append(system_message)

    # 只保留最近 50 条
    if len(room_messages[room]) > 50:
        room_messages[room] = room_messages[room][-50:]

    socketio.emit('message', system_message, to=room)


@socketio.on('message')
def handle_message(data):
    username = data['username']
    room = data['room']
    msg = data['msg']

    if room not in room_messages:
        room_messages[room] = []

    message_data = {
        'type': 'user',
        'sender': username,
        'text': msg,
        'time': datetime.now().strftime('%H:%M')
    }

    # 保存聊天记录
    room_messages[room].append(message_data)

    # 只保留最近 50 条
    if len(room_messages[room]) > 50:
        room_messages[room] = room_messages[room][-50:]

    # 广播给当前房间所有人
    socketio.emit('message', message_data, to=room)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)