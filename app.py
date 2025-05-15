from backend import create_app, db
from flask_socketio import SocketIO

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
app.socketio = socketio  # attach to app for use in routes

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
