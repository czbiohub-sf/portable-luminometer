import RPi.GPIO as GPIO
from adc_constants import *
from luminometer_constants import *
import numpy as np
import time


GPIO.setmode(GPIO.BCM)
GPIO.setup(SHT_1, GPIO.OUT, initial = 0)
GPIO.setup(SHT_PWM, GPIO.OUT, initial = 0)
GPIO.setup(NSLEEP, GPIO.OUT, initial = 1)

# Test digital shutter motion
for i in range(10):
	GPIO.output(SHT_PWM, 0)
	GPIO.output(SHT_1, 1)
	time.sleep(.5)
	GPIO.output(SHT_PWM, 1)
	GPIO.output(SHT_1, 0)
	time.sleep(.5)

pwm = GPIO.PWM(SHT_PWM, SHT_PWM_FREQ)

pwm.start(1)

dutyRatio = np.linspace(0, 100, 100)

# for dr in dutyRatio:
# 	print(dr)
# 	pwm.ChangeDutyCycle(dr)
# 	time.sleep(0.5)


GPIO.cleanup()
