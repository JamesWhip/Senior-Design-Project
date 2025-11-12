from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import chess
import chess.svg
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Each room_id maps to a chess.Board and game state
rooms = {}


def get_or_create_room(room_id):
    """Retrieve the game room or create a new one."""
    if room_id not in rooms:
        rooms[room_id] = {
            "board": chess.Board(),
            "last_move": None,
            "players": {}  # socket.id -> color
        }
    return rooms[room_id]


def board_svg(board, last_move):
    """Return SVG + turn info for broadcasting."""
    svg = chess.svg.board(board=board, lastmove=last_move, coordinates=True, size=480)
    return {"svg": svg, "turn": "White" if board.turn else "Black"}


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/game/<room_id>")
def game(room_id):
    return render_template("index.html", room_id=room_id)


# ---- SOCKET.IO EVENTS ---- #

@socketio.on("join")
def on_join(data):
    room_id = data["room"]
    room = get_or_create_room(room_id)
    join_room(room_id)

    # Assign color if available
    if "white" not in room["players"].values():
        color = "white"
    elif "black" not in room["players"].values():
        color = "black"
    else:
        color = "spectator"

    room["players"][request.sid] = color

    emit("player_color", {"color": color})
    emit("board_update", board_svg(room["board"], room["last_move"]), room=room_id)
    print(f"Client {request.sid} joined room {room_id} as {color}")


@socketio.on("move")
def handle_move(data):
    room_id = data["room"]
    from_sq, to_sq = data["from"], data["to"]

    room = get_or_create_room(room_id)
    board = room["board"]

    # Check player's color
    player_color = room["players"].get(request.sid)
    if player_color == "spectator":
        return  # spectators can't move

    # Ensure it's their turn
    if (board.turn and player_color != "white") or (not board.turn and player_color != "black"):
        return

    try:
        move = chess.Move.from_uci(from_sq + to_sq)
        if (board.piece_type_at(chess.parse_square(from_sq)) == chess.PAWN and
                chess.square_rank(chess.parse_square(to_sq)) in [0, 7]):
            move.promotion = chess.QUEEN
        if move in board.legal_moves:
            board.push(move)
            room["last_move"] = move
            emit("board_update", board_svg(board, move), room=room_id)
    except Exception as e:
        print("Invalid move:", e)


@socketio.on("undo")
def handle_undo(data):
    room_id = data["room"]
    room = get_or_create_room(room_id)
    if room["board"].move_stack:
        room["board"].pop()
        room["last_move"] = None
        emit("board_update", board_svg(room["board"], None), room=room_id)


@socketio.on("reset")
def handle_reset(data):
    room_id = data["room"]
    room = get_or_create_room(room_id)
    room["board"] = chess.Board()
    room["last_move"] = None
    emit("board_update", board_svg(room["board"], None), room=room_id)


@socketio.on("disconnect")
def handle_disconnect():
    for room_id, room in rooms.items():
        if request.sid in room["players"]:
            del room["players"][request.sid]
            print(f"Client {request.sid} left room {room_id}")
            break


if __name__ == "__main__":
    socketio.run(app, debug=True)
