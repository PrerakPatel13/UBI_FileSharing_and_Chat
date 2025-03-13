from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from flask_socketio import SocketIO, emit, disconnect
import os
import atexit

app = Flask(__name__, static_folder='templates')
app.secret_key = "supersecretkey"
socketio = SocketIO(app, cors_allowed_origins='*')

UPLOAD_FOLDER = os.path.join(os.path.expanduser("~"), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

MAX_USERS = 40
users = {}
logged_in_users = {}
valid_users = {f'dj{i}': f'sa{i}' for i in range(1, 41)}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in valid_users and valid_users[username] == password:
            if len(logged_in_users) >= MAX_USERS:
                return "Max user limit reached. Try again later."
            if username in logged_in_users:
                return "User already logged in from another session. Please log out first."
            session['username'] = username
            logged_in_users[username] = None
            return redirect(url_for('dashboard', username=username))
        else:
            return "Invalid username or password."

    return render_template('login.html')

@app.route('/dashboard/<username>')
def dashboard(username):
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('login'))
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', uploaded_files=uploaded_files, username=username)

@app.route('/logout/<username>')
def logout(username):
    if 'username' in session and session['username'] == username:
        session.pop('username', None)
        if username in logged_in_users:
            logged_in_users.pop(username)
        return redirect(url_for('login'))
    return "Invalid logout request"

@app.route('/upload/<username>', methods=['POST'])
def upload_file(username):
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('login'))
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('dashboard', username=username))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@socketio.on('connect')
def handle_connect():
    if len(users) >= MAX_USERS:
        disconnect()
        return
    user_id = request.sid
    username = session.get('username')
    if username:
        if logged_in_users.get(username):
            disconnect()
            return
        users[user_id] = username
        logged_in_users[username] = user_id
    else:
        disconnect()

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id in users:
        username = users[user_id]
        del users[user_id]
        logged_in_users.pop(username, None)

@socketio.on('message')
def handle_message(data):
    user_id = request.sid
    if user_id in users:
        emit('message', {'name': users[user_id], 'text': data['text']}, broadcast=True)

def clear_uploads():
    if os.path.exists(UPLOAD_FOLDER):
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

atexit.register(clear_uploads)

if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        clear_uploads()
