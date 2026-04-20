from flask import Flask, send_from_directory
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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

    emit('history', room_messages[room])

    system_message = f'系统消息：{username} 进入了房间 {room}'
    socketio.emit('message', system_message, to=room)


@socketio.on('message')
def handle_message(data):
    username = data['username']
    room = data['room']
    msg = data['msg']

    if room not in room_messages:
        room_messages[room] = []

    full_message = f'{username}: {msg}'
    room_messages[room].append(full_message)

    if len(room_messages[room]) > 50:
        room_messages[room] = room_messages[room][-50:]

    socketio.emit('message', full_message, to=room)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)