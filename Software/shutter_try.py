import RPi.GPIO as GPIO
import time


# Device user input pushbuttons, BCM pins
BTN_1 = 3
BTN_2 = 26
BTN_3 = 19
BZ_PIN = 12

AIN1 = 16
AIN2 = 13
BIN1 = 5
BIN2 = 6

delay = 0.5
nTimes = 5

if __name__ == "__main__":

	GPIO.setmode(GPIO.BCM)
	GPIO.setup(BTN_1, GPIO.OUT)
	GPIO.output(BTN_1,0)
	GPIO.setup(BTN_1, GPIO.IN)
	GPIO.setup(BTN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(BTN_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	GPIO.setup(BZ_PIN, GPIO.OUT)
	GPIO.setup(AIN1, GPIO.OUT)
	GPIO.setup(AIN2, GPIO.OUT)
	GPIO.setup(BIN1, GPIO.OUT)
	GPIO.setup(BIN2, GPIO.OUT)

	BZ = GPIO.PWM(BZ_PIN,261.62 )

	try:
		BZ.start(50)
		time.sleep(delay)
		BZ.stop()

		GPIO.output(AIN1,0)
		GPIO.output(AIN2,0)
		GPIO.output(BIN1,0)
		GPIO.output(BIN2,0)

		for i in range(nTimes):
			
			print(i)
			# Issue a forward pulse
			GPIO.output(BIN1,0)
			GPIO.output(BIN2,1)

			GPIO.output(AIN1,0)
			GPIO.output(AIN2,1)

			time.sleep(delay)

			# Issue a negative pulse
			GPIO.output(BIN1,1)
			GPIO.output(BIN2,0)

			GPIO.output(AIN1,1)
			GPIO.output(AIN2,0)
			time.sleep(delay)

		GPIO.output(AIN1,0)
		GPIO.output(AIN2,0)
		GPIO.output(BIN1,0)
		GPIO.output(BIN2,0)
	finally:
		GPIO.cleanup()
