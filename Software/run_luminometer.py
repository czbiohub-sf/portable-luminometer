
from luminometer import Luminometer
from lumiscreen import LumiScreen
import time
import concurrent.futures
import queue

q = queue.Queue()

if __name__ == "__main__":

	# Parse command line args
	parser = argparse.ArgumentParser()
	parser.add_argument('--shutterTime', '-s', type=int, required=True, help="Shutter time in seconds")
	parser.add_argument('--integration', '-i', type=int, required=True, help="Integration time in seconds")
	parser.add_argument('--title','-t',type=str, required=True, help="Title for output file (no extension)")
	args, _ = parser.parse_known_args()

	shutterTime = args.shutterTime
	integrationTime_seconds = args.integration
	title = args.title

	shutterA = LumiShutter(AIN1, AIN2, NFAULT, NSLEEP)
	shutterB = LumiShutter(BIN1, BIN2, NFAULT, NSLEEP)
	screen = LumiScreen()
	buzzer = LumiBuzzer(BUZZ)
	Luminometer = Luminometer(shutterA, shutterB, screen, buzzer)

	try:
		Luminometer.measure(integrationTime_seconds, shutterTime)
		#Luminometer.measureUponButtonPress(integrationTime_seconds, shutterTime)
		Luminometer.writeToFile(title)

	except KeyboardInterrupt:
		pass

	finally:
		GPIO.cleanup()

