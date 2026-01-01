import socketio

# Create a Socket.IO Settings (Async Mode for FastAPI)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Define Events
@sio.event
async def connect(sid, environ):
    print(f"[Socket] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[Socket] Client disconnected: {sid}")

@sio.event
async def audio_ack(sid, data):
    # Optional: confirm client received chunk
    pass
