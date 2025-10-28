# motor_control.py
# Runs two stepper motors in tandem for a CoreXY-style belt layout.
# Move exactly N tiles along +X/-X or +Y/-Y; enable before and disable after.

import RPi.GPIO as GPIO
import time
from math import copysign

# ---- pin map (BCM) ----
DIR1, STEP1 = 26, 19   # Motor A (left)
DIR2, STEP2 = 16, 12   # Motor B (right)
EN1,  EN2   = 6, 5     # Active-low enables

# ---- user knobs ----
INVERT_DIR1 = False     # flip if motor A direction is backwards
INVERT_DIR2 = False     # flip if motor B direction is backwards
STEP_DELAY  = 0.0008    # s between step edges (~625 Hz per phase)
STEPS_PER_TILE = 500   # <<< adjust later; rough first guess

# ---- setup ----
GPIO.setmode(GPIO.BCM)
for p in (DIR1, STEP1, DIR2, STEP2, EN1, EN2):
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(EN1, GPIO.HIGH)  # start disabled (EN=HIGH)
GPIO.output(EN2, GPIO.HIGH)

# ---- helpers ----
def _enable_both(on: bool):
    # EN is active-low
    GPIO.output(EN1, GPIO.LOW if on else GPIO.HIGH)
    GPIO.output(EN2, GPIO.LOW if on else GPIO.HIGH)

def _set_dir(pin, cw, invert=False):
    GPIO.output(pin, GPIO.HIGH if (cw != invert) else GPIO.LOW)

def _step_once(pin):
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    GPIO.output(pin, GPIO.LOW)
    time.sleep(STEP_DELAY)

def _move_locked(steps_a: int, steps_b: int):
    """
    Synchronous stepping for straight moves (|steps_a| == |steps_b|),
    which is true for pure X or pure Y moves in CoreXY.
    """
    n = max(abs(steps_a), abs(steps_b))
    sa = 1 if steps_a >= 0 else -1
    sb = 1 if steps_b >= 0 else -1

    # directions already set by caller; just clock both together
    for _ in range(n):
        # If one axis is zero, it simply won't toggle (not used here)
        if steps_a != 0:
            GPIO.output(STEP1, GPIO.HIGH)
        if steps_b != 0:
            GPIO.output(STEP2, GPIO.HIGH)
        time.sleep(STEP_DELAY)

        if steps_a != 0:
            GPIO.output(STEP1, GPIO.LOW)
        if steps_b != 0:
            GPIO.output(STEP2, GPIO.LOW)
        time.sleep(STEP_DELAY)

# ---- public API ----
def move_x_tiles(n_tiles: float, positive=True):
    """
    Move carriage along board X by n_tiles. positive=True -> +X, else -X.
    CoreXY: ΔA = ΔX, ΔB = ΔX  (both same direction)
    """
    steps = int(round(n_tiles * (STEPS_PER_TILE if positive else -STEPS_PER_TILE)))

    # set both motor directions the same
    cw = steps >= 0
    _set_dir(DIR1, cw, invert=INVERT_DIR1)
    _set_dir(DIR2, cw, invert=INVERT_DIR2)

    _enable_both(True)
    _move_locked(abs(steps), abs(steps))   # equal step counts
    _enable_both(False)

def move_y_tiles(n_tiles: float, positive=True):
    """
    Move carriage along board Y by n_tiles. positive=True -> +Y, else -Y.
    CoreXY: ΔA = +ΔY, ΔB = -ΔY  (equal & opposite)
    """
    steps = int(round(n_tiles * (STEPS_PER_TILE if positive else -STEPS_PER_TILE)))

    # Motor A follows sign of steps; Motor B is opposite
    cw_a = steps >= 0
    cw_b = not cw_a

    _set_dir(DIR1, cw_a, invert=INVERT_DIR1)
    _set_dir(DIR2, cw_b, invert=INVERT_DIR2)

    _enable_both(True)
    _move_locked(abs(steps), abs(steps))   # equal magnitude, opposite direction set by DIR pins
    _enable_both(False)

# ---- demo ----
if __name__ == "__main__":
    try:
        # +X by 1 tile, short pause, then +Y by 1 tile
        move_x_tiles(1, positive=True)
        time.sleep(1.0)
        move_y_tiles(1, positive=True)
        time.sleep(1.0)
        # back to start
        move_y_tiles(1, positive=False)
        move_x_tiles(1, positive=False)
    finally:
        GPIO.output(EN1, GPIO.HIGH)
        GPIO.output(EN2, GPIO.HIGH)
        GPIO.cleanup()
