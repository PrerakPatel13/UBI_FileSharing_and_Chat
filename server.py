from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__, static_folder='templates')
socketio = SocketIO(app)

UPLOAD_FOLDER = os.path.join(os.path.expanduser("~"), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def clear_uploaded_files():
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

clear_uploaded_files()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

users = {}

@app.route('/')
def index():
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', uploaded_files=uploaded_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return render_template('upload_success.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@socketio.on('connect')
def handle_connect():
    user_id = request.sid
    users[user_id] = {'name': 'IP ' + request.remote_addr}
    print(f'User {user_id} connected')

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    del users[user_id]
    print(f'User {user_id} disconnected')

@socketio.on('message')
def handle_message(data):
    user_id = request.sid
    emit('message', {'name': users[user_id]['name'], 'text': data['text']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
