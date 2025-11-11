# motor_control_median.py — FULL-STEP + “median-lane” path
# Moves a chess piece from a start square to an end square using:
#   +0.5 tile (into horizontal median) → long axis in a vertical aisle → side-hop into column → -0.5 tile (into center)
# Assumptions:
#   • CoreXY mechanics (A,B) with ΔA=ΔX+ΔY, ΔB=ΔX-ΔY
#   • Carriage is homed so that (0,0) is the CENTER of A1
#   • Board squares are TILE_INCHES pitch, 8×8 board with A1 bottom-left
#   • No obstacle checking yet (pure geometric plan as requested)

import RPi.GPIO as GPIO
import time
from typing import List, Tuple

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
TILE_INCHES    = 1.5
STEPS_PER_TILE = int(round(STEPS_PER_IN * TILE_INCHES))
HALF_TILE_STEPS = STEPS_PER_TILE // 2

# Soft limits (inches from origin center A1) — keep generous margins
X_MAX_IN, Y_MAX_IN = 13.0, 14.0
X_MAX_STEPS = int(round(STEPS_PER_IN * X_MAX_IN))
Y_MAX_STEPS = int(round(STEPS_PER_IN * Y_MAX_IN))

# Optional inversions (UNCHANGED)
INVERT_DIR1 = True
INVERT_DIR2 = False
INVERT_X    = False

# Step timing: (one HIGH+LOW pair per microstep pulse)
STEP_DELAY = 0.0036   # seconds; increase if you skip

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
    if step_a: GPIO.output(STEP1, GPIO.HIGH)
    if step_b: GPIO.output(STEP2, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    if step_a: GPIO.output(STEP1, GPIO.LOW)
    if step_b: GPIO.output(STEP2, GPIO.LOW)
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

def _mag_on(): _mag_pwm.ChangeDutyCycle(MAG_DUTY_MOVE)
def _mag_off(): _mag_pwm.ChangeDutyCycle(0)

# ----------------------------- Unit conversions -----------------------------
def tiles_to_steps_x(delta_tiles: float) -> int:
    if INVERT_X:
        delta_tiles = -delta_tiles
    return int(round(delta_tiles * STEPS_PER_TILE))

def tiles_to_steps_y(delta_tiles: float) -> int:
    return int(round(delta_tiles * STEPS_PER_TILE))

# ----------------------------- Chess helpers -----------------------------
def parse_square(sq: str) -> Tuple[int,int]:
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

def center_of_square_tiles(col0: int, row0: int) -> Tuple[float,float]:
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

# ----------------------------- Path planning helpers -----------------------------
def _sign(v: float) -> int:
    return (v > 0) - (v < 0)

# ----------------------------- Path planning (median-lane, X-first) -----------------------------
def plan_median_xfirst(start_sq: str, end_sq: str) -> List[Tuple[str, float]]:
    """
    New plan:
        +0.5 Y                       # enter horizontal aisle above start
        (xe - xs - 0.5*sgn(dx)) X    # traverse in the vertical aisle beside destination column
        (ye - ys) Y                  # long Y move within the aisle
        (0.5*sgn(dx)) X              # side-hop into the destination column center
        -0.5 Y                       # drop into the destination square center

    If dx == 0 (same column), the ±0.5 X hops vanish (sgn=0).
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
    segs.append(("Y", -0.5))                 # drop into destination center
    return segs

def execute_segments_with_piece(segments: List[Tuple[str, float]], corner_dwell_s: float = 0.10):
    """
    Execute a preplanned list of axis-aligned segments while holding the piece.
    Magnet ON for the whole path; small dwell between segments.
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

# ----------------------------- High-level: move one piece -----------------------------
def move_piece(start_sq: str, end_sq: str):
    """
    Full sequence:
      1) Travel (no piece) to start center
      2) Plan median-lane path (X-first, aisle-correct)
      3) Execute while holding the piece
    """
    cs, rs = parse_square(start_sq)
    ce, re = parse_square(end_sq)

    # 1) Travel to start
    print(f"[Go] Moving empty carriage to {start_sq}...")
    go_to_square_center(cs, rs)
    print(f"[Pick] At {start_sq} center. Engaging magnet and moving to {end_sq} via medians...")

    # 2) Plan + 3) Execute
    segs = plan_median_xfirst(start_sq, end_sq)
    execute_segments_with_piece(segs)

    print(f"[Done] Reached {end_sq}. Magnet released.")

# ----------------------------- Diagnostics -----------------------------
def report():
    x_in = x_pos_steps / STEPS_PER_IN
    y_in = y_pos_steps / STEPS_PER_IN
    print(f"Pos ≈ ({x_in:.3f} in, {y_in:.3f} in) | "
          f"Tiles ≈ ({x_pos_steps/STEPS_PER_TILE:.3f}, {y_pos_steps/STEPS_PER_TILE:.3f})")

# ----------------------------- Script entry -----------------------------
if __name__ == "__main__":
    try:
        print(f"Config: steps/in={STEPS_PER_IN}, steps/tile≈{STEPS_PER_TILE} (tile={TILE_INCHES}\")")
        print("Assuming carriage is homed at A1 center (0,0).")
        print('Enter moves as "E4, E5". Commands: pos, quit')

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

            # Expect "E4, E5"
            try:
                start_sq, end_sq = [s.strip().upper() for s in raw.split(",")]
                parse_square(start_sq)
                parse_square(end_sq)
            except Exception:
                print('Format error. Try: E4, E5   (or "pos", "quit")')
                continue

            try:
                move_piece(start_sq, end_sq)
                report()
            except Exception as e:
                print(f"[ERROR] {e}")

    finally:
        # Always leave hardware safe
        try:
            _mag_off()
            _mag_pwm.stop()
        except Exception:
            pass
        GPIO.output(EN1, GPIO.HIGH)
        GPIO.output(EN2, GPIO.HIGH)
        GPIO.cleanup()
