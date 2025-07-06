from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state storage
rooms = {}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/station/<station>')
def station(station):
    return render_template(f'{station}.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('join')
def handle_join(data):
    room = data['room']
    station = data['station']
    
    # Create room if new
    if room not in rooms:
        rooms[room] = {
            'state': {
                'heading': {'x': 0, 'y': 0},  # Horizontal and vertical headings
                'speed': 0,
                'altitude': 0,  # Initial altitude in meters
                'alert': 'NORMAL',
                'systems': {
                    'weapons': 100,
                    'shields': 100,
                    'hull': 100,
                    'power': 100,
                    'hull_message': 'All systems nominal'
                }
            },
            'players': {}
        }
    
    # Join room and station namespace
    join_room(room)
    join_room(f"{room}_{station}")
    
    # Update player list
    rooms[room]['players'][request.sid] = {
        'station': station,
        'name': data.get('name', 'Player')
    }
    
    # Send initial state to new player
    emit('state_update', rooms[room]['state'], room=room)
    print(f"Player joined {room} as {station}")

@socketio.on('gm_update')
def handle_gm_update(data):
    room = data['room']
    if room in rooms:
        # Update game state
        rooms[room]['state'].update(data['changes'])
        
        # Broadcast to all players
        emit('state_update', rooms[room]['state'], room=room)
        print(f"GM updated room {room}: {data['changes']}")

@socketio.on('player_action')
def handle_player_action(data):
    room = data['room']
    if room in rooms:
        action = data['action']
        value = data.get('value')
        state = rooms[room]['state']
        
        # Handle different station actions
        if action == 'update_heading_x':
            state['heading']['x'] = value
        elif action == 'update_heading_y':
            state['heading']['y'] = value
        elif action == 'update_speed':
            state['speed'] = value
        elif action == 'fire_weapons':
            state['systems']['weapons'] = max(0, state['systems']['weapons'] - 10)
        elif action == 'adjust_power':
            state['systems']['power'] = value
        elif action == 'set_alert':
            state['alert'] = value
        elif action == 'set_frequency':
            state['frequency'] = value
            
        # Broadcast updated state
        emit('state_update', state, room=room)
        
        # Notify GM specifically when headings are confirmed
        if action in ['update_heading_x', 'update_heading_y']:
            emit('gm_notification', {
                'type': 'heading_update',
                'heading': state['heading']
            }, room=room)
            print(f"Heading update notification sent to GM: x={state['heading']['x']}°, y={state['heading']['y']}°")
        
        print(f"Player action in {room}: {action} = {value}")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)
    # Remove player from rooms
    for room in rooms.values():
        if request.sid in room['players']:
            del room['players'][request.sid]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
