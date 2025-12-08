
import socketio
import threading

SERVER_URL = "http://localhost:5000"
sio = socketio.Client()


import requests
import chess

GANTRY_SERVER_URL = "http://172.17.88.122:3000"   # change to your server IP

def send_move_to_gantry(start, end, is_capture):
    print("Request:", is_capture)
    r = requests.get(f"{GANTRY_SERVER_URL}/move", params={"start": start, "end": end, "capture": is_capture})
    print("Server replied:", r.text)

def init_connection(board):
    global room
    global Board
    Board = board

    print(f"🔌 Connecting to {SERVER_URL} ...")
    try:
        sio.connect(SERVER_URL)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Ask which room to join
    room = input("🏠 Enter room name (e.g., game1, test, etc.): ").strip() or "default"
    sio.emit("join", {"room": room})
    print(f"📥 Joined room: {room}")

# --------------------
# Event Handlers
# --------------------

@sio.event
def connect():
    global connected
    connected = True
    print("✅ Connected to chess server.")


@sio.event
def disconnect():
    global connected
    connected = False
    print("❌ Disconnected from chess server.")


@sio.on("message")
def on_message(msg):
    print(f"💬 {msg}")

@sio.on("player_color")
def on_color(data):
    global player_color
    player_color = data.get("color")
    print(f"💬 Player color set to {player_color}")

@sio.on("board_update")
def on_board_update(data):
    global current_turn
    current_turn = data.get("turn", "Unknown")

    fen = data.get("fen")
    if fen is None:
        print("⚠️ board_update received with no FEN field.")
        return

    print(f"\n♟ Board updated — {current_turn}'s turn.")
    print(f"FEN: {fen}")

    Board.set_board(chess.Board(fen))
    
    if (data.get("turn") == player_color):
        uci_move = data.get("last_move").upper()
        capture = bool(data.get("capture"))
        print(capture)

        send_move_to_gantry(uci_move[0:2], uci_move[2:4], capture)
    


# --------------------
# Command Functions
# --------------------

def send_move(uci):
    if len(uci) < 4:
        print("❗ Invalid format. Use like: move e2e4")
        return
    from_sq, to_sq = uci[:2], uci[2:4]
    sio.emit("move", {"room": room, "from": from_sq, "to": to_sq})
    print(f"➡️ Sent move: {from_sq}->{to_sq}")


def send_undo():
    sio.emit("undo", {"room": room})
    print("↩️  Undo sent.")


def send_reset():
    sio.emit("reset", {"room": room})
    print("🔄  Board reset.")


def send_random():
    sio.emit("random_move", {"room": room})
    print("🎲 Random move sent.")