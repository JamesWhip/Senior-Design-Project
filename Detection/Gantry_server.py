# server.py — Socket.IO server for smart chessboard (Python)

import socketio
from aiohttp import web
import threading

# Create Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

PORT = 3000  # Must match the Pi's SOCKETIO_SERVER_URL port


# ---- HTTP ROUTES ----

# Simple homepage
async def index(request):
    return web.Response(text="Chessboard Socket.IO server is running.")

app.router.add_get("/", index)


# Move endpoint:
#   http://<IP>:3000/move?start=E2&end=E4
async def move_handler(request):
    start = request.rel_url.query.get("start")
    end   = request.rel_url.query.get("end")
    capture   = request.rel_url.query.get("capture")

    if not start or not end:
        return web.Response(
            status=400,
            text="Usage: /move?start=E2&end=E4"
        )

    start = start.upper().strip()
    end   = end.upper().strip()

    print(f"[HTTP] Request to move: {start} -> {end}")

    # Broadcast to all connected Pis
    await sio.emit("move_piece", {"start": start, "end": end, "capture": capture})

    return web.Response(text=f"Emitted move_piece: {start} -> {end}, capture: {capture}")

app.router.add_get("/move", move_handler)


# ---- SOCKET.IO EVENTS ----

@sio.event
async def connect(sid, environ):
    print("[IO] Client connected:", sid)


@sio.event
async def move_piece_done(sid, data):
    print("[IO] move_piece_done from Pi:", data)


@sio.event
async def disconnect(sid):
    print("[IO] Client disconnected:", sid)



# ---- SERVER START FUNCTION ----

def run_server_blocking():
    """Run the Socket.IO server normally (blocking)."""
    print(f"Chessboard server listening on port {PORT}")
    print(f"Visit http://localhost:{PORT}/ in a browser to check.")
    web.run_app(app, port=PORT)


def start_server_in_thread():
    """
    Start the Socket.IO server in a new background thread.
    Returns the thread object.
    """
    thread = threading.Thread(target=run_server_blocking, daemon=True)
    thread.start()
    print("[THREAD] Socket.IO server started in background thread.")
    return thread


# If run directly, start normally
if __name__ == "__main__":
    run_server_blocking()