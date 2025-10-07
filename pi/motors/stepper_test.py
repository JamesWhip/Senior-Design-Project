# two-motor stepper test for Raspberry Pi (full-step mode: MS1/2/3 = LOW)
# M1: DIR=21, STEP=20
# M2: DIR=16, STEP=12

import RPi.GPIO as GPIO
import time

# --- pins ---
DIR1, STEP1 = 21, 20
DIR2, STEP2 = 16, 12

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for p in [DIR1, STEP1, DIR2, STEP2]:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

# set DIR and wait a moment so the driver latches the direction before stepping
def dir_set(dir_pin, cw=True, t_settle=0.010):
    GPIO.output(dir_pin, GPIO.HIGH if cw else GPIO.LOW)
    time.sleep(t_settle)

# generate N steps on one motor at a fixed safe rate
def step_many(step_pin, n_steps, pulse_delay=0.003):
    for _ in range(n_steps):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(pulse_delay)     # step high width
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(pulse_delay)     # low time between steps

# visible jogs: a few full steps per "click" so motion is obvious
def jog_visible(step_pin, clicks, steps_per_click=5, pulse_delay=0.003, pause_between=0.20):
    for _ in range(clicks):
        step_many(step_pin, steps_per_click, pulse_delay=pulse_delay)
        time.sleep(pause_between)

try:
    # ----- Motor 1: visible jogs -----
    print("M1: CW jogs...")
    dir_set(DIR1, cw=True)
    jog_visible(STEP1, clicks=10, steps_per_click=5, pulse_delay=0.003, pause_between=0.20)

    print("M1: CCW jogs...")
    dir_set(DIR1, cw=False)
    jog_visible(STEP1, clicks=10, steps_per_click=5, pulse_delay=0.003, pause_between=0.20)

    # ----- Motor 1: continuous -----
    print("M1: CW continuous...")
    dir_set(DIR1, cw=True)
    step_many(STEP1, n_steps=400, pulse_delay=0.003)

    print("M1: CCW continuous...")
    dir_set(DIR1, cw=False)
    step_many(STEP1, n_steps=400, pulse_delay=0.003)

    # ----- Motor 2: visible jogs -----
    print("M2: CW jogs...")
    dir_set(DIR2, cw=True)
    jog_visible(STEP2, clicks=10, steps_per_click=5, pulse_delay=0.003, pause_between=0.20)

    print("M2: CCW jogs...")
    dir_set(DIR2, cw=False)
    jog_visible(STEP2, clicks=10, steps_per_click=5, pulse_delay=0.003, pause_between=0.20)

    # ----- Motor 2: continuous -----
    print("M2: CW continuous...")
    dir_set(DIR2, cw=True)
    step_many(STEP2, n_steps=400, pulse_delay=0.003)

    print("M2: CCW continuous...")
    dir_set(DIR2, cw=False)
    step_many(STEP2, n_steps=400, pulse_delay=0.003)

    # ----- Both together (lock-step) -----
    print("Both: CW...")
    dir_set(DIR1, cw=True)
    dir_set(DIR2, cw=True)
    for _ in range(400):
        GPIO.output(STEP1, GPIO.HIGH); GPIO.output(STEP2, GPIO.HIGH)
        time.sleep(0.003)
        GPIO.output(STEP1, GPIO.LOW);  GPIO.output(STEP2, GPIO.LOW)
        time.sleep(0.003)

    print("Both: CCW...")
    dir_set(DIR1, cw=False)
    dir_set(DIR2, cw=False)
    for _ in range(400):
        GPIO.output(STEP1, GPIO.HIGH); GPIO.output(STEP2, GPIO.HIGH)
        time.sleep(0.003)
        GPIO.output(STEP1, GPIO.LOW);  GPIO.output(STEP2, GPIO.LOW)
        time.sleep(0.003)

    print("Done.")
finally:
    GPIO.cleanup()
