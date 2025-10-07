import RPi.GPIO as GPIO
import time

# === Motor 1 ===
DIR1  = 21
STEP1 = 20

# === Motor 2 ===
DIR2  = 16
STEP2 = 12

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# setup both motors
for pin in [DIR1, STEP1, DIR2, STEP2]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === helper function to step one motor ===
def step_motor(step_pin, n_steps, d_start=0.005, d_min=0.001, ramp=300):
    for i in range(n_steps):
        # simple ramp from d_start to d_min
        if i < ramp:
            delay = d_start - (d_start - d_min) * (i / float(ramp))
        else:
            delay = d_min
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)

try:
    # ---- Motor 1 test ----
    print("Motor 1 CW...")
    GPIO.output(DIR1, True)
    step_motor(STEP1, 400)

    time.sleep(0.5)
    print("Motor 1 CCW...")
    GPIO.output(DIR1, False)
    step_motor(STEP1, 400)

    # ---- Motor 2 test ----
    time.sleep(0.5)
    print("Motor 2 CW...")
    GPIO.output(DIR2, True)
    step_motor(STEP2, 400)

    time.sleep(0.5)
    print("Motor 2 CCW...")
    GPIO.output(DIR2, False)
    step_motor(STEP2, 400)

    # ---- Both together ----
    print("Both motors CW together...")
    GPIO.output(DIR1, True)
    GPIO.output(DIR2, True)
    for i in range(400):
        GPIO.output(STEP1, GPIO.HIGH)
        GPIO.output(STEP2, GPIO.HIGH)
        time.sleep(0.0015)
        GPIO.output(STEP1, GPIO.LOW)
        GPIO.output(STEP2, GPIO.LOW)
        time.sleep(0.0015)

    time.sleep(0.5)
    print("Both motors CCW together...")
    GPIO.output(DIR1, False)
    GPIO.output(DIR2, False)
    for i in range(400):
        GPIO.output(STEP1, GPIO.HIGH)
        GPIO.output(STEP2, GPIO.HIGH)
        time.sleep(0.0015)
        GPIO.output(STEP1, GPIO.LOW)
        GPIO.output(STEP2, GPIO.LOW)
        time.sleep(0.0015)

    print("Done.")
finally:
    GPIO.cleanup()
