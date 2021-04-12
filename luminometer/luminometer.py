#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time, math, csv, argparse
import os
import RPi.GPIO as GPIO
import concurrent.futures
import threading
import queue
from typing import List
from statistics import mean, stdev

from adc_constants import *
from luminometer_constants import *
from lumiscreen import LumiScreen, LumiMode
from ads131m08_reader import ADS131M08Reader, bytes_to_readable, CRCError

"""
 TODO:
- Complete button callbacks
- Switch to PWM drive of shutters (Future, in V1.2)
- Test with hardware
- Write auto-exposure function
- Add detail to display messages (s.e.m. and/or SNR, measurement duration)
"""


class HBridgeFault(Exception):
    pass

class LumiBuzzer():
	def __init__(self, buzzPin: int):
		try:
			self._buzzPin = int(buzzPin)
		except TypeError:
			print("Pin value not convertible to integer!")
			raise
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(buzzPin, GPIO.OUT)
		self._pwm = GPIO.PWM(self._buzzPin, FREQ)

	def buzz(self):
		self._pwm.start(50)
		time.sleep(BUZZ_S)
		self._pwm.stop()

class LumiShutter():
	# Uses RPi BCM pinout
	# Written to operate a TI DRV8833 H-bridge chip.
	# Each instance of this class drives just one channel; create a second instance to drive two channels.

	def __init__(self, fwdPin: int, revPin: int, faultPin: int, sleepPin: int):
		try:
			self._fwdPin = int(fwdPin)
			self._revPin = int(revPin)
			self._faultPin = int(faultPin)
			self._sleepPin = int(sleepPin)
		except TypeError:
			print('Pin value not convertible to integer!')
			raise

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._fwdPin, GPIO.OUT, initial = 0)
		GPIO.setup(self._revPin, GPIO.OUT, initial = 0)
		GPIO.setup(self._sleepPin, GPIO.OUT, initial = 1)
		GPIO.setup(self._faultPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.output(self._sleepPin, 1)

		# Set up edge detection for this channel. Passing on exception because two shutters
		# share the same driver chip, and will have the same pin. RuntimeError is raised
		# if you try to add event detect twice to the same pin. 
		try:
			GPIO.add_event_detect(self._faultPin, GPIO.FALLING, callback=self._faultDetected)
		except RuntimeError:
			pass

		self._lock = threading.Lock()


	def actuate(self, action: str, driveTime: float = SHUTTER_ACTUATION_TIME):
		
		try:
			action = str(action)
		except TypeError:
			print("\naction must be a string!")
			return
		if not self._lock.locked():
			with self._lock:
				if action == 'open':
					print(f"\nOpening shutter")
					GPIO.output([self._fwdPin,self._revPin], (1,0))
					time.sleep(driveTime)
					self.brake()

				elif action == 'close':
					print(f"\nClosing shutter")
					GPIO.output([self._fwdPin,self._revPin], (0,1))
					time.sleep(driveTime)
					self.brake()

				else:
					print(f"\nShutter command not recognized!")

		return

	def rest(self):
		GPIO.output([self._fwdPin, self._revPin], (0,0))

	def brake(self):
		GPIO.output([self._fwdPin, self._revPin], (1,1))

	def _faultDetected(self, channel):
		# Callback for handling an H-bridge fault pin event
		# Ref datasheet:
		# https://www.ti.com/lit/ds/symlink/drv8833.pdf?ts=1617084507643&ref_url=https%253A%252F%252Fwww.google.com%252F
		print('\nH-bridge fault detected!')
		raise HBridgeFault

class Luminometer():

	def __init__(self):

		try:
			self._adc = ADS131M08Reader()
			self._adc.setup_adc(SPI_CE, channels=[0,1])
			self._simulate = False
		except Exception as e:
			print("Error creating ADC reader!")
			print(e)
			self._simulate = True

		self.display = LumiScreen()
		self.shutterA = LumiShutter(AIN1, AIN2, NFAULT, NSLEEP)
		self.shutterB = LumiShutter(BIN1, BIN2, NFAULT, NSLEEP)
		self.buzzer = LumiBuzzer(BUZZ)
		self._btn1 = BTN_1
		self._btn2 = BTN_2
		self._btn3 = BTN_3
		self._powerOn = True
		self._measuring = False
		self._darkIsStored = False
		self._measurementIsDone = False
		self._darkRef = [0.0, 0.0]

		try: 
			self.adc_status_print()
		except Exception as e:
			print('Could not print ADC status!')

		self._crcErrs = 0
		self._measureLock = threading.Lock()

		# Set up channels for button pushes
		GPIO.setup(self._btn1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Add callback for button pushes
		GPIO.add_event_detect(self._btn1, GPIO.FALLING, callback=self._btn1_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn2, GPIO.FALLING, callback=self._btn2_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn3, GPIO.FALLING, callback=self._btn3_callback, bouncetime=200)

		# Start handling incoming ADC data
		if self._simulate:
			print("SIMULATION MODE: Starting timer callback")
			self._cbTimer = threading.Timer(SAMPLE_TIME_S, self._cb_adc_data_ready, args=(DRDY,))
			self._cbTimer.start()
		else:
			GPIO.add_event_detect(self._adc._DRDY, GPIO.FALLING, callback=self._cb_adc_data_ready)

		# Create thread-safe queues for hardware jobs
		self._display_q = queue.Queue(maxsize=1)
		self._shutter_q = queue.Queue(maxsize=1)
		self._measure_q = queue.Queue(maxsize=1)

	def _btn1_callback(self, channel):
		# Handle presses to button 1
		# A short press on button 1 performs a measurement.
		# A long hold on button 1 shuts the system down

		startTime = time.time()
		while not GPIO.input(channel):
			pass

		duration = time.time() - startTime
		print(f"\nButton held for {duration} seconds ")

		if duration > BTN_1_HOLD_TO_POWERDOWN_S:
			self._powerOn = False
			print('Powering off')

			try:
				self._display_q.put((LumiMode.TITLE, 'Powering off'))
			except queue.Full:
				pass

		elif not self._measureLock.locked():
			try:
				self._measure_q.put_nowait((DEF_DARK_TIME,True))
			except queue.Full:
				print('\nAlready busy measuring')

	def _btn2_callback(self, channel):
		# Handle presses to button 2
		startTime = time.time()
		while not GPIO.input(channel):
			pass

		duration = time.time() - startTime
		print(f"Not implemented")
		# try:
		# 	if not self._measureLock.locked():
		# 		self._measure_q.put_nowait('reference')
		# except queue.Full:
		# 	print('\nAlready busy measuring')
	
	def _btn3_callback(self, channel):
		# Handle presses to button 3
		try:
			if not self._measureLock.locked():
				self._measure_q.put_nowait((0,False))
		except queue.Full:
			print('\nAlready busy measuring')

	def adc_status_print(self):
		print("ID")
		d = self._adc.read_register(ID_ADDR)
		print(bytes_to_readable(d)[0])
		print()

		print("MODE")
		d = self._adc.read_register(MODE_ADDR)
		print(bytes_to_readable(d)[0])
		print()

		print("CLOCK")
		d = self._adc.read_register(CLOCK_ADDR)
		print(bytes_to_readable(d)[0])
		print()

		print("CFG")
		d = self._adc.read_register(CFG_ADDR)
		print(bytes_to_readable(d)[0])
		print()

		print("STATUS")
		d = self._adc.read_register(STATUS_ADDR)
		print(bytes_to_readable(d)[0])
		print()

	def measure(self, \
		measure_time: int = 30, \
		dark: bool = False):
		"""
		Arguments:
		measure_time is the duration of the entire measurement, in seconds
		dark is a boolean specifying whether to store the current measurement as 'dark' reference;
		to be subtractred from all future (non-dark) measurements.

		Outputs to command line and display: A +/- s.e.m.
											 B +/- s.e.m.
		Where A and B are the gated measurements for each channel, in units of volts,
		and s.e.m. are standard errors of the mean.
	
		This function computes gated datapoints as the mean of a shutter open period,
		subtracted by the mean of its flanking closed periods. It will always start
		and end a measurement with shutter-closed periods.

		Ex. If the measure_time is set to 7 seconds and the SHUTTER_PERIOD is 1 second, then 
		there will be 3 shutter-open periods and 4 shutter-closed periods.

		_|-|_|-|_|-|_

		"""
		if not self._measuring:
			with self._measureLock:

				# Confirm to user that a dark measurement is being performed
				if dark:
					try:
						self._display_q.put((LumiMode.TITLE, 'DARK REF IN PROGRESS'))
					except queue.Full:
						pass

				# Close shutters
				try:
					self._shutter_q.put('close')
				except queue.Full:
					pass

				self._resetBuffers(measure_time)

				t0 = time.time()

				try:
					self._measuring = True
					sampleCount = 0

					# Start data acquisition loop
					while self._rsc < self.nRawSamples:

						# Do this once each time a full cycle (closed-open-closed) has completed:
						if (self._sc > sampleCount) and ((self._sc % 2)==0) and (self._sc > 2):
							print(f"\nMeasure: sample count = {self._sc}")

							self.dataA = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, SKIP_SAMPLES)
							self.dataA -= self._darkRef[0]
							print(f"Sensor A after {int(self._sc/2)} cycles: {FM_PER_V*mean(self.dataA):.4f} fM")
							print(f"Sensor A raw: {self.rawdataA[self._rsc-1]:.4f}")

							self.dataB = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, SKIP_SAMPLES)
							self.dataB -= self._darkRef[1]
							print(f"Sensor B after {int(self._sc/2)} cycles: {FM_PER_V*mean(self.dataB):.4f} fM")
							print(f"Sensor B raw: {self.rawdataB[self._rsc-1]:.4f}")

							self.semA = stdev(self.dataA)/math.sqrt(self.nSamples)
							self.semB = stdev(self.dataB)/math.sqrt(self.nSamples)

							duration_s = time.time() - t0

							# Update display with intermediate results
							try:
								self._display_q.put_nowait((\
									LumiMode.RESULT, \
									self._darkIsStored,\
									self._measurementIsDone,\
									self.dataA,\
									self.semA,\
									self.dataB,\
									self.semB,\
									duration_s))
							except queue.Full:
								print('\nDisplay queue full. Could not display result')

							sampleCount += 1

					self.dataA = self.gateTrace(self.rawdataA, self.shutter_samples)
					self.dataB = self.gateTrace(self.rawdataB, self.shutter_samples)
					self.resultA = mean(self.dataA)
					self.resultB = mean(self.dataB)
					self.semA = stdev(self.dataA)/math.sqrt(self.nSamples)
					self.semB = stdev(self.dataB)/math.sqrt(self.nSamples)

					if dark:
						self._darkRef = [self.dataA, self.dataB]
						self._darkIsStored = True

					print(f"\nSensor A final result: {FM_PER_V*self.resultA:.4f} +/- {FM_PER_V*self.semA:.4f} (s.e.m.) ")
					print(f"\nSensor B final result: {FM_PER_V*self.resultB:.4f} +/- {FM_PER_V*self.semB:.4f} (s.e.m.) ")

					self.buzzer.buzz()
				
				except Exception as exc:
					self.writeToFile('Interrupted_')
					print(f'\nException occured during measurement: {exc}')
				finally:
					t1 = time.time()
					self._measuring = False

				print(f"\n{self._rsc} samples in {self.t1 - self.t0} seconds. Sample rate of {self._rsc / (t1 - t0)} Hz")
				print(f"{self._crcErrs} CRC Errors encountered.")

			return

	def _cb_adc_data_ready(self, channel):
		# Callback function executed when data ready is asserted from ADC
		# The callback also queues the shutter actions, in order to stay synchronized 
		# with the data readout.

		if self._simulate:
			# Simulation mode
			d = [0.0, 0.0]

		else:
			try:
				# Read sensor
				d = self._adc.read()

			# ADC communication error
			except CRCError:
				self._crcErrs += 1
				return
	
		if self._measuring and (self._rsc < self.nRawSamples):
			self.rawdataA[self._rsc] = d[0]
			self.rawdataB[self._rsc] = d[1]

			# Close shutters
			if self._rsc % (2*self.shutter_samples) == 0:
				try:
					self._shutter_q.put_nowait('close')
				except queue.Full:
					pass

			# Open shutters
			elif self._rsc % self.shutter_samples == 0:
				try:
					self._shutter_q.put_nowait('open')
				except queue.Full:
					pass

			self._rsc += 1
			self._sc = int(math.floor(self._rsc/self.shutter_samples))
		return

	def _resetBuffers(self, measure_time: int):

			self._measurementIsDone = False

			# The actual number of samples is taken as the ceiling of however many 
			# full open and closed periods it takes to complete the measurement
			self.shutter_samples = int(math.ceil(SHUTTER_PERIOD/SAMPLE_TIME_S))

			# Number of shutter-open periods
			self.nSamples = int(math.floor(measure_time/(2*SHUTTER_PERIOD)))

			# Number of shutter closed periods
			self.nDark = self.nSamples + 1

			# Raw samples are continous and include open and closed periods
			self.nRawSamples = self.shutter_samples*(self.nSamples + self.nDark)

			self.rawdataA = self.nRawSamples*[None]
			self.rawdataB = self.nRawSamples*[None]

			# Counters
			self._rsc = self._sc = self._crcErrs = 0

	def writeToFile(self, title):

		with open(title + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(self.nRawSamples):
				csvWriter.writerow((self.rawdataA[i], self.rawdataB[i]))

		with open(title + '_gated' + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(len(self.dataA)):
				csvWriter.writerow((self.dataA[i], self.dataB[i]))

	def gateTrace(self, rawData: List[float], gateSize: int) -> List[float]:
		# Helper method that computes the mean of each even chunk of data, subtracted by the mean of the flanking odd
		# chunks of data. The chunk size is specified by gateSize, and the total size of the rawData should be an odd
		# multiple of gateSize, so that every even chunk has two flanking odd chunks.

		# The function will disregard raw data that does not consist of a complete odd multiple of the gateSize.

		nPeriods = int(len(rawData) / gateSize)

		if nPeriods < 3:
			print("Raw data size must be greater than three times gateSize!")
			return [0.0]

		# Process only up the last odd-numbered period
		if nPeriods % 2 == 0:
			nPeriods = nPeriods -1

		print(f"Gate trace: nPeriods = {nPeriods}")

		samples = []

		for i in range(gateSize, gateSize*nPeriods, 2*gateSize):
			sample = mean(rawData[(i+SKIP_SAMPLES):i+(gateSize-1)])
			darkBefore = mean(rawData[(i-gateSize+SKIP_SAMPLES):(i-1)])
			darkAfter = mean(rawData[(i+gateSize+SKIP_SAMPLES):(i+2*gateSize - 1)])
			samples.append( sample - 0.5*(darkBefore + darkAfter))

		return samples 


	def run(self):
		try:
			with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:

				# Start a future for thread to submit work through the queue
				future_result = { \
					executor.submit(Luminometer.shutterA.actuate, 'close'): 'SHUTTER A CLOSED', \
					executor.submit(Luminometer.shutterB.actuate, 'close'): 'SHUTTER B CLOSED'  \
					}

				print('Ready and waiting for button pushes...')

				# Main realtime loop:
				while self._powerOn:

					# Check for status of the futures which are currently working
					done, not_done = concurrent.futures.wait(future_result, timeout=0.05, \
						return_when=concurrent.futures.FIRST_COMPLETED)
					
					# Measure queue has size 1 and will not add additional items to the queue
					while not self._measure_q.empty():
						try:
							measureType = self._measure_q.get_nowait()
						except queue.Empty:
							pass

						future_result[executor.submit(self.measure, measureType)] = measureType

					# Shutter queue has size 1 and will not add additional items to the queue
					while not self._shutter_q.empty():

						# Fetch an action from the queue
						try:
							action = self._shutter_q.get_nowait()
						except queue.Empty:
							pass

						# Submit shutter actions
						future_result[executor.submit(self.shutterA.actuate, action)] = "Shutter A: " + action
						future_result[executor.submit(self.shutterB.actuate, action)] = "Shutter B: " + action

					# Display queue has size 2 and will not add additional items to the queue
					# If there is an incoming message, start a new future
					while not self._display_q.empty():

						# Fetch a job from the queue
						try:
							message = self._display_q.get_nowait()
						except queue.Empty:
							pass

						# Start the load operation and mark the future with its URL
						future_result[executor.submit(self.display.parser, message)] = "Message displayed: " + message[0]

					# Process any completed futures
					for future in done:
						result = future_result[future]
						try:
							data = future.result()
						except Exception as exc:
							print('%r generated an exception: %s' % (result, exc))

						# Remove the now completed future
						del future_result[future]
		except KeyboardInterrupt:
			pass

if __name__ == "__main__":

	# # Parse command line args
	# parser = argparse.ArgumentParser()
	# parser.add_argument('--shutterTime', '-s', type=int, required=True, help="Shutter time in seconds")
	# parser.add_argument('--integration', '-i', type=int, required=True, help="Integration time in seconds")
	# parser.add_argument('--title','-t',type=str, required=True, help="Title for output file (no extension)")
	# args, _ = parser.parse_known_args()

	# shutterTime = args.shutterTime
	# integrationTime_seconds = args.integration
	# title = args.title

	Luminometer = Luminometer()
	try:
		Luminometer.run()
	except Exception as exc:
		print(f'Encountered exception: {exc}')
	finally:
		GPIO.cleanup()
		del(Luminometer)
		
		# Power down system
		os.system('sudo poweroff')


