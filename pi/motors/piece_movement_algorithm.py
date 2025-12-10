# motor_control_median.py — FULL-STEP + “median-lane” path
# Moves a chess piece from a start square to an end square using:
#   +0.5 tile (into horizontal median) → long axis in a vertical aisle → side-hop into column → -0.5 tile (into center)
# Assumptions:
#   • CoreXY mechanics (A,B) with ΔA=ΔX+ΔY, ΔB=ΔX-ΔY
#   • Carriage is homed so that (0,0) is the CENTER of A1
#   • Board squares are TILE_INCHES pitch, 8×8 board with A1 bottom-left
#   • No obstacle checking yet (pure geometric plan as requested)
#
#   • Socket.IO client to receive move commands over Wi-Fi
#   • Event: "move_piece" with payload {"start": "E4", "end": "E5", "capture": false}
#   • CLI mode still available with: python3 motor_control_median.py cli
#   • Capture handling:
#       - Remove captured piece from END square to a capture rack along the H-side
#       - Then move attacking piece START -> END using normal median lane

import RPi.GPIO as GPIO
import time
from typing import List, Tuple
import sys
import socketio  # pip install "python-socketio[client]"
import signal    # for out-of-band “home” command via SIGUSR1

# ----------------------------- Socket.IO config -----------------------------
# Change this to James' backend URL
SOCKETIO_SERVER_URL = "http://172.17.88.122:3000"

sio = socketio.Client()

# ----------------------------- Pins (BCM) -----------------------------
DIR1, STEP1 = 26, 19   # Motor A (left)
DIR2, STEP2 = 16, 12   # Motor B (right)
EN1,  EN2   = 6, 5     # DRV8825 EN (active-low)

# Magnet driver (XY-MOS)
MAG_PIN        = 18     # PWM input on XY-MOS
MAG_PWM_FREQ   = 1000   # Hz
MAG_DUTY_MOVE  = 100    # % duty while moving (tune if needed)

# ----------------------------- Motion constants -----------------------------
# Drive train (FULL STEP)
MICROSTEP      = 1
STEPS_PER_REV  = 200         # 1.8° motor
PULLEY_TEETH   = 20          # GT2-20T
GT2_PITCH_MM   = 2.0         # 2 mm/tooth
BELT_PER_REV_MM = PULLEY_TEETH * GT2_PITCH_MM         # 40 mm/rev
STEPS_PER_MM   = (STEPS_PER_REV * MICROSTEP) / BELT_PER_REV_MM  # 5.0
STEPS_PER_IN   = int(round(STEPS_PER_MM * 25.4))                  # ≈127

# Chessboard pitch (center-to-center) — keep your current value
TILE_INCHES    = 1.6562  # inches
STEPS_PER_TILE = int(round(STEPS_PER_IN * TILE_INCHES))
HALF_TILE_STEPS = STEPS_PER_TILE // 2

# Soft limits (inches from origin center A1) — keep generous margins
X_MAX_IN, Y_MAX_IN = 14.5, 14.0
X_MAX_STEPS = int(round(STEPS_PER_IN * X_MAX_IN))
Y_MAX_STEPS = int(round(STEPS_PER_IN * Y_MAX_IN))

# Optional inversions (UNCHANGED)
INVERT_DIR1 = True
INVERT_DIR2 = False
INVERT_X    = False

# Step timing: (one HIGH+LOW pair per microstep pulse)
STEP_DELAY = 0.003   # seconds; increase if you skip

# ----------------------------- Capture zone config -----------------------------
# Capture rack along the H-side (right side of the board).
# Coordinates are in "tile units" with A1 center = (0,0).
# We place captured pieces in a vertical column near the H-file, spaced closer
# than one tile so we can fit many of them.
X_MAX_TILES = X_MAX_STEPS / STEPS_PER_TILE
Y_MAX_TILES = Y_MAX_STEPS / STEPS_PER_TILE

CAPTURE_X_TILES          = min(8.5, X_MAX_TILES - 0.1)  # near/right of H-file, inside soft limit
CAPTURE_Y_START_TILES    = 0.5                          # a bit above A-rank edge
CAPTURE_Y_SPACING_TILES  = 0.5                           # tighter spacing than board
CAPTURE_MAX_SLOTS        = int(
    (Y_MAX_TILES - CAPTURE_Y_START_TILES) // CAPTURE_Y_SPACING_TILES
)

capture_index = 0  # how many pieces have been parked so far

# ----------------------------- GPIO setup -----------------------------
GPIO.setmode(GPIO.BCM)
for p in (DIR1, STEP1, DIR2, STEP2, EN1, EN2):
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(EN1, GPIO.HIGH)  # disabled at idle
GPIO.output(EN2, GPIO.HIGH)

GPIO.setup(MAG_PIN, GPIO.OUT, initial=GPIO.LOW)
_mag_pwm = GPIO.PWM(MAG_PIN, MAG_PWM_FREQ)
_mag_pwm.start(0)  # off at idle

# ----------------------------- Kinematics helpers -----------------------------
x_pos_steps = 0  # “world” position in steps from A1 center
y_pos_steps = 0

def _enable_drives(on: bool):
    GPIO.output(EN1, GPIO.LOW if on else GPIO.HIGH)
    GPIO.output(EN2, GPIO.LOW if on else GPIO.HIGH)

def _set_dir(pin: int, cw: bool, invert: bool = False):
    GPIO.output(pin, GPIO.HIGH if (cw != invert) else GPIO.LOW)

def _pulse(step_a: bool, step_b: bool):
    if step_a:
        GPIO.output(STEP1, GPIO.HIGH)
    if step_b:
        GPIO.output(STEP2, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    if step_a:
        GPIO.output(STEP1, GPIO.LOW)
    if step_b:
        GPIO.output(STEP2, GPIO.LOW)
    time.sleep(STEP_DELAY)

def _move_corexy(dx_steps: int, dy_steps: int):
    """
    Execute a straight move in carriage X/Y. For our path we only issue
    pure X or pure Y segments, so |ΔA|==|ΔB| and a simple loop suffices.
    """
    dA = dx_steps + dy_steps
    dB = dx_steps - dy_steps

    _set_dir(DIR1, (dA >= 0), invert=INVERT_DIR1)
    _set_dir(DIR2, (dB >= 0), invert=INVERT_DIR2)

    steps = max(abs(dA), abs(dB))
    step_a = (dA != 0)
    step_b = (dB != 0)

    for _ in range(steps):
        _pulse(step_a, step_b)

def _mag_on():
    _mag_pwm.ChangeDutyCycle(MAG_DUTY_MOVE)

def _mag_off():
    _mag_pwm.ChangeDutyCycle(0)

# ----------------------------- Unit conversions -----------------------------
def tiles_to_steps_x(delta_tiles: float) -> int:
    if INVERT_X:
        delta_tiles = -delta_tiles
    return int(round(delta_tiles * STEPS_PER_TILE))

def tiles_to_steps_y(delta_tiles: float) -> int:
    return int(round(delta_tiles * STEPS_PER_TILE))

# ----------------------------- Chess helpers -----------------------------
def parse_square(sq: str) -> Tuple[int, int]:
    """
    Convert 'E4' to zero-based (col,row) = (4,3) with A1=(0,0).
    col: A..H => 0..7 ; row: 1..8 => 0..7
    """
    sq = sq.strip().upper()
    if len(sq) != 2 or sq[0] < 'A' or sq[0] > 'H' or sq[1] < '1' or sq[1] > '8':
        raise ValueError(f"Bad square '{sq}'")
    col = ord(sq[0]) - ord('A')
    row = int(sq[1]) - 1
    return (col, row)

def center_of_square_tiles(col0: int, row0: int) -> Tuple[float, float]:
    """
    Return center in 'tile units' with A1 at (0,0). So E4 center is (4,3).
    """
    return float(col0), float(row0)

# ----------------------------- Motion primitives -----------------------------
def move_x_tiles(delta_tiles: float):
    """Pure X move by tiles (can be fractional)."""
    global x_pos_steps
    dx = tiles_to_steps_x(delta_tiles)
    target = x_pos_steps + dx
    if target < 0 or target > X_MAX_STEPS:
        raise RuntimeError("X soft-limit exceeded")
    _move_corexy(dx_steps=dx, dy_steps=0)
    x_pos_steps = target

def move_y_tiles(delta_tiles: float):
    """Pure Y move by tiles (can be fractional)."""
    global y_pos_steps
    dy = tiles_to_steps_y(delta_tiles)
    target = y_pos_steps + dy

    # --- Rounding safety near origin ---
    # If we're within ±2 steps of 0, just snap to exactly 0
    if -2 <= target <= 2:
        dy = -y_pos_steps   # move exactly back to 0
        target = 0

    if target < 0 or target > Y_MAX_STEPS:
        raise RuntimeError("Y soft-limit exceeded")

    _move_corexy(dx_steps=0, dy_steps=dy)
    y_pos_steps = target

def go_to_square_center(col0: int, row0: int):
    """
    Travel (no piece) from current pos to the exact center of (col0,row0),
    using straight X then Y. Simple and safe (no carry).
    """
    cx, cy = center_of_square_tiles(col0, row0)
    cur_x_tiles = x_pos_steps / STEPS_PER_TILE
    cur_y_tiles = y_pos_steps / STEPS_PER_TILE

    _enable_drives(True)
    move_x_tiles(cx - cur_x_tiles)
    move_y_tiles(cy - cur_y_tiles)
    _enable_drives(False)

def _sign(v: float) -> int:
    return (v > 0) - (v < 0)

def approach_square_with_early_magnet(col0: int, row0: int, early_tiles: float = 0.5):
    """
    Travel to (col0,row0) but switch magnet ON early_tiles before the center
    along the final leg. Net motion is identical to go_to_square_center:
    still X then Y; we just split the last leg into [leg - early] + [early].
    """
    cx, cy = center_of_square_tiles(col0, row0)
    cur_x_tiles = x_pos_steps / STEPS_PER_TILE
    cur_y_tiles = y_pos_steps / STEPS_PER_TILE

    dx = cx - cur_x_tiles
    dy = cy - cur_y_tiles

    _enable_drives(True)
    _mag_off()  # ensure we start this approach with magnet off

    # Always keep axis order: X then Y.
    if abs(dy) > 1e-6:
        # --- Y is the final leg ---
        # 1) Do full X with magnet off
        if abs(dx) > 1e-6:
            move_x_tiles(dx)

        # 2) Split Y into (dy - early) + early, if we have enough length
        sgn_y = _sign(dy)
        if abs(dy) > early_tiles + 1e-6:
            lead_y = dy - sgn_y * early_tiles
            if abs(lead_y) > 1e-6:
                move_y_tiles(lead_y)
            # Turn magnet on for the last early_tiles as we slide under the piece
            _mag_on()
            move_y_tiles(sgn_y * early_tiles)
        else:
            # Short Y move: just turn magnet on for the whole Y leg
            _mag_on()
            move_y_tiles(dy)
    else:
        # --- No Y leg; use X as the final leg ---
        sgn_x = _sign(dx)
        if abs(dx) > early_tiles + 1e-6:
            lead_x = dx - sgn_x * early_tiles
            if abs(lead_x) > 1e-6:
                move_x_tiles(lead_x)
            _mag_on()
            move_x_tiles(sgn_x * early_tiles)
        else:
            # Already very close: just engage magnet and finish X
            _mag_on()
            if abs(dx) > 1e-6:
                move_x_tiles(dx)

    _enable_drives(False)
    # IMPORTANT: leave magnet ON so the next move (median path) starts with
    # the piece already held.

# ----------------------------- Path planning (median-lane, X-first) -----------------------------
def plan_median_xfirst(start_sq: str, end_sq: str) -> List[Tuple[str, float]]:
    """
    Median-lane path from start_sq to end_sq (board squares):
        +0.5 Y                       # enter horizontal aisle above start
        (xe - xs - 0.5*sgn(dx)) X    # traverse in the vertical aisle beside destination column
        (ye - ys) Y                  # long Y move within the aisle
        (0.5*sgn(dx)) X              # side-hop into the destination column center
        -0.5..-0.75 Y                # drop into the destination square center
    """
    cs, rs = parse_square(start_sq)
    ce, re = parse_square(end_sq)

    xs, ys = center_of_square_tiles(cs, rs)
    xe, ye = center_of_square_tiles(ce, re)

    dx = xe - xs
    dy = ye - ys
    s = _sign(dx)

    segs: List[Tuple[str, float]] = []
    segs.append(("Y", +0.5))                 # into horizontal aisle
    segs.append(("X", dx - 0.5 * s))         # run X inside vertical aisle next to dest column
    segs.append(("Y", dy))                   # long Y while in aisle
    if s != 0:
        segs.append(("X", 0.5 * s))          # step sideways into column center
    segs.append(("Y", -0.7))                # drop into destination center
    return segs

def plan_median_from_current_to_target_tiles(target_x_tiles: float,
                                             target_y_tiles: float) -> List[Tuple[str, float]]:
    """
    Same median-lane idea, but from the *current* carriage position (in tiles)
    to an arbitrary tile coordinate (used for capture rack).
    """
    cur_x_tiles = x_pos_steps / STEPS_PER_TILE
    cur_y_tiles = y_pos_steps / STEPS_PER_TILE

    dx = target_x_tiles - cur_x_tiles
    dy = target_y_tiles - cur_y_tiles
    s = _sign(dx)

    segs: List[Tuple[str, float]] = []
    segs.append(("Y", +0.5))                 # into horizontal aisle
    segs.append(("X", dx - 0.5 * s))         # traverse X inside aisle
    segs.append(("Y", dy))                   # long Y in aisle
    if s != 0:
        segs.append(("X", 0.5 * s))          # side hop toward target center
    segs.append(("Y", -0.7))                # drop down toward target
    return segs

def execute_segments_with_piece(segments: List[Tuple[str, float]], corner_dwell_s: float = 0.10):
    """
    Execute a preplanned list of axis-aligned segments while holding the piece.
    Magnet is on during this path (usually already engaged slightly before call).
    """
    _enable_drives(True)
    _mag_on()
    try:
        for axis, tiles in segments:
            if tiles == 0:
                continue
            if axis == "X":
                move_x_tiles(tiles)
            else:
                move_y_tiles(tiles)
            time.sleep(corner_dwell_s)  # settle at corners/centers
    finally:
        _mag_off()
        _enable_drives(False)

# ----------------------------- Capture rack helpers -----------------------------
def alloc_capture_slot_tiles() -> Tuple[float, float]:
    """
    Allocate the next capture position along the H-side capture rack.
    Returns target (x_tiles, y_tiles).
    """
    global capture_index
    if capture_index >= CAPTURE_MAX_SLOTS:
        raise RuntimeError("Capture zone is full")

    cx = CAPTURE_X_TILES
    cy = CAPTURE_Y_START_TILES + capture_index * CAPTURE_Y_SPACING_TILES
    capture_index += 1
    return cx, cy

# ----------------------------- High-level: move one piece -----------------------------
def move_piece(start_sq: str, end_sq: str):
    """
    Normal (non-capture) move:
      1) Travel (no piece at first) to start square, with magnet turning on
         ~0.5 tile before the center so it grabs the piece while sliding under.
      2) Plan median-lane path (X-first, aisle-correct)
      3) Execute while holding the piece
    """
    cs, rs = parse_square(start_sq)
    ce, re = parse_square(end_sq)

    # 1) Travel to start with early magnet engagement
    print(f"[Go] Moving empty carriage to {start_sq} (magnet will turn on ~0.5 tile early)...")
    approach_square_with_early_magnet(cs, rs, early_tiles=0.5)
    print(f"[Pick] At {start_sq} with magnet engaged. Moving to {end_sq} via medians...")

    # 2) Plan + 3) Execute
    segs = plan_median_xfirst(start_sq, end_sq)
    execute_segments_with_piece(segs)

    print(f"[Done] Reached {end_sq}. Magnet released.")

def capture_then_move_piece(start_sq: str, end_sq: str):
    """
    Capture sequence:
      1) Go to END square first, pick up the piece being captured.
      2) Move that piece to the capture rack along the H-side of the board.
      3) Then move the attacking piece from START -> END using the normal median path.

    This avoids ever trying to have two pieces in the same square under the magnet.
    """
    # --- 1) Remove and park the captured piece ---
    ce, re = parse_square(end_sq)
    print(f"[Cap] Moving to {end_sq} to pick up captured piece...")
    approach_square_with_early_magnet(ce, re, early_tiles=0.5)

    cx, cy = alloc_capture_slot_tiles()
    print(f"[Cap] Carrying captured piece from {end_sq} to capture rack at "
          f"({cx:.2f} tiles, {cy:.2f} tiles)...")
    segs = plan_median_from_current_to_target_tiles(cx, cy)
    execute_segments_with_piece(segs)
    print(f"[Cap] Captured piece parked. Now moving attacker {start_sq} -> {end_sq}...")

    # --- 2) Move the attacking piece into the now-empty square ---
    move_piece(start_sq, end_sq)

def go_home_a1():
    """
    Convenience move: return carriage (no piece) to the A1 center.
    This assumes the software position is still accurate (no skipped steps).
    """
    print("[Home] Returning to A1 center (A1)...")
    _mag_off()  # make sure we're not holding a piece
    # A1 is (col,row) = (0,0)
    go_to_square_center(0, 0)
    print("[Home] At A1 center.")

# ----------------------------- Diagnostics -----------------------------
def report():
    x_in = x_pos_steps / STEPS_PER_IN
    y_in = y_pos_steps / STEPS_PER_IN
    print(
        f"Pos ≈ ({x_in:.3f} in, {y_in:.3f} in) | "
        f"Tiles ≈ ({x_pos_steps / STEPS_PER_TILE:.3f}, {y_pos_steps / STEPS_PER_TILE:.3f})"
    )

# ----------------------------- Signal handler for “home” -----------------
def _handle_sigusr1(signum, frame):
    """
    Systemd / OS-level “home” command:
    Send SIGUSR1 to this process to return carriage to A1 center.
    """
    print("\n[SIG] SIGUSR1 received — homing carriage to A1...")
    try:
        go_home_a1()
        report()
    except Exception as e:
        print(f"[SIG] Error while homing: {e}")

# Register the handler so it’s active in both CLI and Socket.IO modes
signal.signal(signal.SIGUSR1, _handle_sigusr1)

# ----------------------------- Hardware cleanup -----------------------------
def hardware_cleanup():
    # Always leave hardware safe
    try:
        _mag_off()
        _mag_pwm.stop()
    except Exception:
        pass
    try:
        GPIO.output(EN1, GPIO.HIGH)
        GPIO.output(EN2, GPIO.HIGH)
    except Exception:
        pass
    GPIO.cleanup()

# ----------------------------- CLI mode (old behavior) -----------------------------
def run_cli_mode():
    print(f"Config: steps/in={STEPS_PER_IN}, steps/tile≈{STEPS_PER_TILE} (tile={TILE_INCHES}\")")
    print("Assuming carriage is homed at A1 center (0,0).")
    print('Enter moves as "E4, E5" for normal moves or "E4xE5" for captures.')
    print('Commands: pos, home, quit')

    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        low = raw.lower()

        if low in ("q", "quit", "exit"):
            break
        if low in ("p", "pos", "where"):
            report()
            continue
        if low in ("h", "home", "origin", "a1"):
            go_home_a1()
            report()
            continue

        capture_flag = False

        # Capture syntax: E4xE5 (no comma)
        if "x" in low and "," not in raw:
            try:
                start_sq, end_sq = [s.strip().upper() for s in low.split("x")]
                parse_square(start_sq)
                parse_square(end_sq)
                capture_flag = True
            except Exception:
                print('Format error. Try: E4xE5 for captures, or "E4, E5" for normal moves.')
                continue
        else:
            # Normal syntax: "E4, E5"
            try:
                start_sq, end_sq = [s.strip().upper() for s in raw.split(",")]
                parse_square(start_sq)
                parse_square(end_sq)
            except Exception:
                print('Format error. Try: E4, E5   (or "pos", "quit")')
                continue

        try:
            if capture_flag:
                capture_then_move_piece(start_sq, end_sq)
            else:
                move_piece(start_sq, end_sq)
            report()
        except Exception as e:
            print(f"[ERROR] {e}")

# ----------------------------- Socket.IO handlers -----------------------------
@sio.event
def connect():
    print("[NET] Connected to Socket.IO server")

@sio.event
def disconnect():
    print("[NET] Disconnected from Socket.IO server")

@sio.on("move_piece")
def on_move_piece(data):
    """
    Expected payload shape:
        { "start": "E4", "end": "E5", "capture": "false" }

    If capture is true, we:
      1) Remove the piece on 'end' to the capture rack
      2) Then move the piece from 'start' to 'end'
    """
    try:
        start_sq = data.get("start", "").strip().upper()
        end_sq   = data.get("end", "").strip().upper()
        capture_flag = str(data.get("capture", "")).lower() == "true"
        print(data.get("capture"))

        print(f"[NET] Received move_piece: {start_sq} -> {end_sq} (capture={capture_flag})")

        # Validate squares before moving
        parse_square(start_sq)
        parse_square(end_sq)

        if capture_flag:
            capture_then_move_piece(start_sq, end_sq)
        else:
            move_piece(start_sq, end_sq)
        report()

        # Optional: emit ack back to server
        sio.emit("move_piece_done", {
            "start": start_sq,
            "end": end_sq,
            "capture": capture_flag,
            "status": "ok",
        })
    except Exception as e:
        print(f"[NET ERROR] {e}")
        try:
            sio.emit("move_piece_done", {
                "start": data.get("start"),
                "end": data.get("end"),
                "capture": data.get("capture"),
                "status": "error",
                "message": str(e),
            })
        except Exception:
            pass

def run_socketio_mode():
    print(f"Config: steps/in={STEPS_PER_IN}, steps/tile≈{STEPS_PER_TILE} (tile={TILE_INCHES}\")")
    print("Assuming carriage is homed at A1 center (0,0).")
    print(f"[NET] Connecting to Socket.IO server at {SOCKETIO_SERVER_URL} ...")
    sio.connect(SOCKETIO_SERVER_URL)
    print("[NET] Waiting for move commands (event: 'move_piece')...")
    sio.wait()  # block here and process events

# ----------------------------- Script entry -----------------------------
if __name__ == "__main__":
    try:
        # If you want the old terminal behavior:
        #   python3 motor_control_median.py cli
        if len(sys.argv) > 1 and sys.argv[1].lower() == "cli":
            run_cli_mode()
        else:
            run_socketio_mode()
    except KeyboardInterrupt:
        print("\n[SYS] KeyboardInterrupt — shutting down.")
    finally:
        hardware_cleanup()

# ----------------------------- Systemd service instructions -----------------------------
# Stop the service: sudo systemctl stop chessbot.service
# Restart: sudo systemctl restart chessbot.service
# Disable autostart:sudo systemctl disable chessbot.service
# View logs: journalctl -u chessbot.service -f
# Activate virtual environment in motors folder: source .venv/bin/activate
# Run in CLI mode: cd ~/senior-design/motors
#                  python3 piece_movement_algorithm.py cli
# Home while in server mode: sudo systemctl kill -s SIGUSR1 chessbot.service
# ----------------------------------------------------------------------------------------
