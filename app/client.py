import socketio
import time
import threading

SERVER_URL = "http://localhost:5000"
sio = socketio.Client()

current_turn = None
connected = False
room = None


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


@sio.on("board_update")
def on_board_update(data):
    global current_turn
    current_turn = data.get("turn", "Unknown")
    print(f"\n♟ Board updated — {current_turn}'s turn.")
    print(f"SVG updated ({len(data['svg'])} bytes).")
    with open(f"board_{room}.svg", "w") as f:
        f.write(data["svg"])
    print(f"💾 Saved board to board_{room}.svg")


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


# --------------------
# CLI Thread
# --------------------

def input_thread():
    print("\n🎮 Commands:")
    print("  move e2e4   - Make a move")
    print("  undo        - Undo last move")
    print("  reset       - Reset game")
    print("  random      - Random legal move")
    print("  exit        - Quit\n")

    while True:
        try:
            cmd = input("> ").strip().lower()
            if not cmd:
                continue
            if cmd.startswith("move"):
                parts = cmd.split()
                if len(parts) == 2:
                    send_move(parts[1])
                else:
                    print("❗ Usage: move e2e4")
            elif cmd == "undo":
                send_undo()
            elif cmd == "reset":
                send_reset()
            elif cmd == "random":
                send_random()
            elif cmd in ("exit", "quit"):
                sio.disconnect()
                break
            else:
                print("❓ Unknown command.")
        except (KeyboardInterrupt, EOFError):
            sio.disconnect()
            break


# --------------------
# Main Program
# --------------------

def main():
    global room
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

    threading.Thread(target=input_thread, daemon=True).start()

    try:
        while connected:
            time.sleep(1)
    except KeyboardInterrupt:
        sio.disconnect()
        print("\n👋 Exiting client.")


if __name__ == "__main__":
    main()
