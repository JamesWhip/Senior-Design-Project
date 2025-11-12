# motor_control.py — FULL-STEP
# Interactive CoreXY mover with soft limits and tile-based commands.

import RPi.GPIO as GPIO
import time

# ---- pins (BCM) ----
DIR1, STEP1 = 26, 19   # Motor A (left)
DIR2, STEP2 = 16, 12   # Motor B (right)
EN1,  EN2   = 6, 5     # DRV8825 EN (active-low)
# ---- magnet (XY-MOS) ----
MAG_PIN        = 18     # PWM input on XY-MOS
MAG_PWM_FREQ   = 1000   # Hz; 1 kHz is quiet
MAG_DUTY_MOVE  = 100    # % duty while moving (tune later)


# ---- motion constants (FULL STEP) ----
MICROSTEP      = 1           # << no microstepping
STEPS_PER_REV  = 200         # 1.8° motor
PULLEY_TEETH   = 20          # GT2-20T
GT2_PITCH_MM   = 2.0         # 2 mm/tooth
BELT_PER_REV_MM = PULLEY_TEETH * GT2_PITCH_MM   # 40 mm/rev
STEPS_PER_MM   = (STEPS_PER_REV * MICROSTEP) / BELT_PER_REV_MM  # 5.0
STEPS_PER_IN   = int(round(STEPS_PER_MM * 25.4))                # 127

# chess board guess; update when you measure
TILE_INCHES    = 1
STEPS_PER_TILE = int(round(STEPS_PER_IN * TILE_INCHES))         # 254

# soft limits (inches from origin)
X_MAX_IN, Y_MAX_IN = 13.0, 14.0
X_MAX_STEPS = int(round(STEPS_PER_IN * X_MAX_IN))
Y_MAX_STEPS = int(round(STEPS_PER_IN * Y_MAX_IN))

# direction inversion (set True if one motor runs opposite)
INVERT_DIR1 = False
INVERT_DIR2 = False
# axis-level input inversion (keeps Y as-is)
INVERT_X = True   # set True to flip X commands; False if already correct

# step timing (full-step moves farther per pulse; keep speed sane)
STEP_DELAY = 0.0024   # ~416 Hz → ~3.3 in/s. Increase if you skip steps.

# ---- setup ----
GPIO.setmode(GPIO.BCM)
for p in (DIR1, STEP1, DIR2, STEP2, EN1, EN2):
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(EN1, GPIO.HIGH)  # disabled at idle
GPIO.output(EN2, GPIO.HIGH)
# Magnet setup
GPIO.setup(MAG_PIN, GPIO.OUT, initial=GPIO.LOW)
_mag_pwm = GPIO.PWM(MAG_PIN, MAG_PWM_FREQ)
_mag_pwm.start(0)   # off at idle

# ---- current position (steps from (0,0)) ----
x_pos_steps = 0 # X_MAX_STEPS // 2  # start near center
y_pos_steps = 0 # Y_MAX_STEPS // 2
# Start with carriage at your chosen (0,0). No homing in this script.

# ---- low-level helpers ----
def _enable_both(on=True):
    GPIO.output(EN1, GPIO.LOW if on else GPIO.HIGH)
    GPIO.output(EN2, GPIO.LOW if on else GPIO.HIGH)

def _set_dir(pin, cw, invert=False):
    GPIO.output(pin, GPIO.HIGH if (cw != invert) else GPIO.LOW)

def _pulse_both(step_a: bool, step_b: bool):
    if step_a: GPIO.output(STEP1, GPIO.HIGH)
    if step_b: GPIO.output(STEP2, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    if step_a: GPIO.output(STEP1, GPIO.LOW)
    if step_b: GPIO.output(STEP2, GPIO.LOW)
    time.sleep(STEP_DELAY)

def _move_corexy(dx_steps: int, dy_steps: int):
    """
    Move by dx, dy in carriage space (CoreXY):
    ΔA = ΔX + ΔY,  ΔB = ΔX - ΔY
    For pure X/Y here, |ΔA| == |ΔB|.
    """
    dA = dx_steps + dy_steps
    dB = dx_steps - dy_steps

    _set_dir(DIR1, (dA >= 0), invert=INVERT_DIR1)
    _set_dir(DIR2, (dB >= 0), invert=INVERT_DIR2)

    steps = max(abs(dA), abs(dB))
    for _ in range(steps):
        _pulse_both(step_a=(dA != 0), step_b=(dB != 0))

def _mag_on():
    _mag_pwm.ChangeDutyCycle(MAG_DUTY_MOVE)

def _mag_off():
    _mag_pwm.ChangeDutyCycle(0)

# ---- high-level API ----
def move_x_tiles(n_tiles: int):
    global x_pos_steps
    # flip X if requested (does NOT affect Y math)
    if INVERT_X:
        n_tiles = -n_tiles

    target = x_pos_steps + n_tiles * STEPS_PER_TILE
    if target < 0 or target > X_MAX_STEPS:
        print(f"[BLOCKED] X move exceeds limits (0..{X_MAX_IN} in).")
        return

    _mag_on()
    _enable_both(True)
    _move_corexy(dx_steps=(target - x_pos_steps), dy_steps=0)
    _enable_both(False)
    _mag_off()

    x_pos_steps = target


def move_y_tiles(n_tiles: int):
    global y_pos_steps
    target = y_pos_steps + n_tiles * STEPS_PER_TILE
    if target < 0 or target > Y_MAX_STEPS:
        print(f"[BLOCKED] Y move exceeds limits (0..{Y_MAX_IN} in).")
        return

    _mag_on()
    _enable_both(True)
    _move_corexy(dx_steps=0, dy_steps=(target - y_pos_steps))
    _enable_both(False)
    _mag_off()
    y_pos_steps = target

def report():
    x_in = x_pos_steps / STEPS_PER_IN
    y_in = y_pos_steps / STEPS_PER_IN
    print(f"Pos ≈ ({x_in:.3f} in, {y_in:.3f} in) | "
          f"Tiles ≈ ({x_pos_steps/STEPS_PER_TILE:.3f}, {y_pos_steps/STEPS_PER_TILE:.3f})")

def help_text():
    print(
f"""Commands:
  x +N    -> move +N tiles in +X (use -N for -X)
  y +N    -> move +N tiles in +Y (use -N for -Y)
  pos     -> print current position
  help    -> show this help
  quit    -> exit

Config:
  • FULL STEP (MICROSTEP={MICROSTEP})
  • Steps/in = {STEPS_PER_IN}  |  Steps/tile ≈ {STEPS_PER_TILE} (tile={TILE_INCHES:.3f} in)
  • Soft-limits: X 0..{X_MAX_IN:.1f} in, Y 0..{Y_MAX_IN:.1f} in
"""
    )

# ---- REPL ----
if __name__ == "__main__":
    try:
        help_text()
        while True:
            cmd = input("> ").strip().lower()
            if cmd in ("q", "quit", "exit"):
                break
            if cmd in ("h", "help", "?"):
                help_text(); continue
            if cmd in ("p", "pos", "where"):
                report(); continue

            parts = cmd.split()
            if len(parts) != 2 or parts[0] not in ("x", "y"):
                print("Try: 'x +2', 'y -1', 'pos', 'quit'."); continue

            axis, tiles_str = parts
            try:
                n_tiles = int(tiles_str)
            except ValueError:
                print("Need an integer tile count (e.g., +1, -2)."); continue

            if n_tiles == 0:
                print("No move."); continue

            if axis == "x":
                move_x_tiles(n_tiles)
            else:
                move_y_tiles(n_tiles)

            report()

    finally:
        _mag_pwm.ChangeDutyCycle(0)
        _mag_pwm.stop()
        GPIO.output(EN1, GPIO.HIGH)
        GPIO.output(EN2, GPIO.HIGH)
        GPIO.cleanup()
