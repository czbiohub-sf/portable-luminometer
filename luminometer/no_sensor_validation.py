from luminometer import Luminometer
import RPi.GPIO as GPIO


if __name__ == "__main__":
	lum = Luminometer()

	try:
		data = lum.averageNMeasurements(200)
		print(f"Channel A sensor average: {data[0]}")
		print(f"Channel B sensor average: {data[1]}")
		print(f"SiPM Ref: {data[2]}")
		print(f"SiPM Bias: {data[3]}")
		print(f"34V Supply: {data[4]}")

		print(f"CRC Errors: {lum._crcErrs}")

	except Exception as exc:
		logger.exception(f'Luminometer encountered exception: {exc}')
	finally:
		GPIO.cleanup()
		del(Luminometer)
		