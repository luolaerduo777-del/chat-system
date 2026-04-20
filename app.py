from flask import Flask
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 用字典保存每个房间的聊天记录
# 例如：
# {
#   "math": ["A: 你好", "B: hi"],
#   "english": ["C: hello"]
# }
room_messages = {}


@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']

    join_room(room)

    # 如果这个房间第一次出现，就先创建一个空列表
    if room not in room_messages:
        room_messages[room] = []

    # 把这个房间已有的聊天记录发给当前用户
    emit('history', room_messages[room])

    # 发一条系统消息到这个房间
    system_message = f'系统消息：{username} 进入了房间 {room}'
    socketio.emit('message', system_message, to=room)


@socketio.on('message')
def handle_message(data):
    username = data['username']
    room = data['room']
    msg = data['msg']

    # 防止房间还没初始化
    if room not in room_messages:
        room_messages[room] = []

    full_message = f'{username}: {msg}'

    # 保存到聊天记录里
    room_messages[room].append(full_message)

    # 只保留最近 50 条，避免越存越多
    if len(room_messages[room]) > 50:
        room_messages[room] = room_messages[room][-50:]

    # 发给这个房间里的所有人
    socketio.emit('message', full_message, to=room)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)