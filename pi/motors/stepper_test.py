# V_ref1 = 0.720V
# Current limit = Vref * 2 = 1.440A
# V_ref2 = 0.727V
# Current limit = Vref * 2 = 1.454A

import RPi.GPIO as GPIO
import time

# --- pin map (BCM) ---
DIR1, STEP1 = 26, 19
DIR2, STEP2 = 16, 12
EN1, EN2   = 6, 5

# --- setup ---
GPIO.setmode(GPIO.BCM)
for p in (DIR1, STEP1, DIR2, STEP2, EN1, EN2):
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)

# EN is active-low; start disabled (HIGH) for safety
GPIO.output(EN1, GPIO.HIGH)
GPIO.output(EN2, GPIO.HIGH)

def enable(driver=1, on=True):
    en = EN1 if driver == 1 else EN2
    GPIO.output(en, GPIO.LOW if on else GPIO.HIGH)

def step_motor(dir_pin, step_pin, steps, cw=True, step_delay=0.001):
    GPIO.output(dir_pin, GPIO.HIGH if cw else GPIO.LOW)
    for _ in range(abs(steps)):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(step_delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(step_delay)

def move_driver(driver, steps, cw=True, step_delay=0.001):
    # pick pins
    if driver == 1:
        d, s = DIR1, STEP1
    else:
        d, s = DIR2, STEP2
    # enable, move, disable
    enable(driver, True)
    step_motor(d, s, steps, cw=cw, step_delay=step_delay)
    enable(driver, False)

def chess_move(x_steps, y_steps, x_cw=True, y_cw=True, step_delay=0.001, park_disable=True):
    # example: move X then Y, then disable both to cool
    move_driver(1, x_steps, cw=x_cw, step_delay=step_delay)
    move_driver(2, y_steps, cw=y_cw, step_delay=step_delay)
    if park_disable:
        enable(1, False)
        enable(2, False)

if __name__ == "__main__":
    try:
        # demo: “move a piece” then rest
        chess_move(x_steps=1600, y_steps=800, x_cw=True, y_cw=False, step_delay=0.0008, park_disable=True)
        time.sleep(5)  # idle cool-down window
        # next move...
        chess_move(x_steps=400, y_steps=400, x_cw=False, y_cw=True, step_delay=0.0008, park_disable=True)
    finally:
        # make sure outputs are off if we exit
        GPIO.output(EN1, GPIO.HIGH)
        GPIO.output(EN2, GPIO.HIGH)
        GPIO.cleanup()