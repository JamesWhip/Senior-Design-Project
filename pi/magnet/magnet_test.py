# magnet_test.py
import RPi.GPIO as GPIO, time

MAG_PIN = 18      # GPIO to XY-MOS IN+
FREQ_HZ = 500     # PWM freq; bump to 1–2 kHz if you hear whine
DUTY = 100         # % duty; start low (20–40%)

GPIO.setmode(GPIO.BCM)
GPIO.setup(MAG_PIN, GPIO.OUT, initial=GPIO.LOW)
p = GPIO.PWM(MAG_PIN, FREQ_HZ)

try:
    p.start(DUTY)     # magnet “strength” via duty
    time.sleep(30)    # hold for 10 s
    p.ChangeDutyCycle(0)
finally:
    p.stop()
    GPIO.cleanup()
