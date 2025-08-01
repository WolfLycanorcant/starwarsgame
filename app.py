from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Helper function for deep merging dictionaries
def deep_update(source, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and key in source:
            deep_update(source[key], value)
        else:
            source[key] = value
    return source

rooms = {}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/station/<station>')
def station(station):
    return render_template(f'{station}.html')

@app.route('/Sounds/<filename>')
def serve_sound(filename):
    return send_from_directory('Sounds', filename)

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('join')
def handle_join(data):
    room = data['room']
    station = data['station']
    
    if room not in rooms:
        rooms[room] = {
            'state': {
                'mission_status': 'INITIALIZE',
                'alert': 'GREEN',
                'systems': {
                    'weapons': 100,
                    'power': 100,
                    'hull': 100,
                    'shields': 100,
                    'hull_message': 'All systems nominal'
                },
                'heading': {
                    'x': 0,
                    'y': 0
                },
                'speed': 0,
                'altitude': 0,
                'frequency': '121.5',
                'transmission_status': 'STANDBY',
                'reception_status': 'ACTIVE',
                'signal_strength': 75,
                'last_transmission': None,
                'hidden_frequency': None
            },
            'players': {}
        }
    
    join_room(room)
    join_room(f"{room}_{station}")
    
    rooms[room]['players'][request.sid] = {
        'station': station,
        'name': data.get('name', 'Player')
    }
    
    emit('state_update', rooms[room]['state'], room=room)
    print(f"Player joined {room} as {station}")

@socketio.on('gm_update')
def handle_gm_update(data):
    room = data['room']
    if room in rooms:
        print(f"Server: Received GM update for room {room}")
        print(f"Server: Changes to apply: {data['changes']}")
        
        # Deep merge changes into the state
        deep_update(rooms[room]['state'], data['changes'])
        
        print(f"Server: Updated state: {rooms[room]['state']} (systems: {rooms[room]['state'].get('systems', {})})")
        emit('state_update', rooms[room]['state'], room=room)
        print(f"Server: Broadcasted state update to room {room}")

@socketio.on('player_action')
def handle_player_action(data):
    room = data.get('room')
    action = data.get('action')
    value = data.get('value')
    
    if room not in rooms:
        return
        
    state = rooms[room]['state']
    
    if action == 'set_mission_status':
        state['mission_status'] = value
    elif action == 'set_alert':
        state['alert'] = value
    elif action == 'set_weapons':
        state['systems']['weapons'] = value
    elif action == 'set_power':
        state['systems']['power'] = value
    elif action == 'update_heading_x':
        state['heading']['x'] = value
    elif action == 'update_heading_y':
        state['heading']['y'] = value
    elif action == 'set_speed':
        state['speed'] = value
        emit('state_update', state, room=room)
        emit('gm_notification', {'type': 'speed_update', 'speed': value}, room=room)
    elif action == 'set_altitude':
        state['altitude'] = value
    elif action == 'set_frequency':
        state['frequency'] = value
    elif action == 'set_hidden_frequency':
        state['hidden_frequency'] = value
    elif action == 'set_transmission_status':
        state['transmission_status'] = value
    elif action == 'set_reception_status':
        state['reception_status'] = value
    elif action == 'set_signal_strength':
        state['signal_strength'] = value
    elif action == 'set_last_transmission':
        state['last_transmission'] = value
    elif action == 'set_command_override_live':
        state['command_override'] = value
    elif action == 'weapon_sound':
        # Broadcast weapon sound to all stations in the room
        emit('player_action', {'action': 'weapon_sound'}, room=room)
        print(f"Broadcasting weapon sound to room {room}")
        return  # Don't emit state_update for weapon sounds
    elif action == 'consume_probe':
        # Update probe count when consumed by gunner station
        state['probesLeft'] = value
        print(f"Probe consumed in {room}, remaining: {value}")
        emit('state_update', state, room=room)
        return
    
    emit('state_update', state, room=room)
    
    if action in ['update_heading_x', 'update_heading_y']:
        emit('gm_notification', {
            'type': 'heading_update',
            'heading': state['heading']
        }, room=room)
        print(f"Heading update notification sent to GM: x={state['heading']['x']}°, y={state['heading']['y']}°")
    
    print(f"Player action in {room}: {action} = {value}")

@socketio.on('weapon_calibration')
def handle_weapon_calibration(data):
    room = data.get('room')
    status = data.get('status')
    
    if room in rooms:
        print(f"Weapon calibration in {room}: {status}")
        # Broadcast calibration status to GM station only
        emit('weapon_calibration', {'status': status}, room=f"{room}_gm")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)
    for room in rooms.values():
        if request.sid in room['players']:
            del room['players'][request.sid]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)