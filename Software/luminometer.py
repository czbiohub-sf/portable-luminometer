#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time, math, csv, argparse
import RPi.GPIO as GPIO
from typing import List
from statistics import mean, stdev

from adc_constants import *
from ads131m08_reader import ADS131M08Reader, bytes_to_readable, CRCError


# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050
SHUTTER_ACTUATION_TIME = 0.05
FM_PER_V = 20000
SKIP_SAMPLES = 3

# BCM pins
# Luminometer pushbuttons
BTN_1 = 3
BTN_2 = 26
BTN_3 = 19

# H-bridge inputs (channel A)
AIN1 = 16
AIN2 = 13
# H-bridge inputs (channel B)
BIN1 = 5
BIN2 = 6
# H-bridge logical I/O
NSLEEP = 1
NFAULT = 0

# Audio element
BUZZ = 12
FREQ = 4000

# SPI Device number
CE = 1

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

	def buzz(self, duration_s: float = 0.2):
		self._pwm.start(50)
		time.sleep(duration_s)
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
		except RuntimeError as rt:
			pass


	def open(self):
		print("Opening shutter")
		GPIO.output([self._fwdPin,self._revPin], (1,0))

	def close(self):
		print('Closing shutter')
		GPIO.output([self._fwdPin, self._revPin], (0,1))

	def rest(self):
		GPIO.output([self._fwdPin, self._revPin], (0,0))

	def brake(self):
		GPIO.output([self._fwdPin, self._revPin], (1,1))

	def _faultDetected(self, channel):
		# Callback for handling an H-bridge fault pin event
		# Ref datasheet:
		# https://www.ti.com/lit/ds/symlink/drv8833.pdf?ts=1617084507643&ref_url=https%253A%252F%252Fwww.google.com%252F
		print('H-bridge fault detected!')
		raise HBridgeFault

class Luminometer():

	def __init__(self, shutterA, shutterB, screen, buzzer):

		self._adc = ADS131M08Reader()
		self._adc.setup_adc(CE, channels=[0,1])
		self._display = screen
		self._display.welcome()

		self.shutterA = shutterA
		self.shutterB = shutterB
		self._buzzer = buzzer

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

	def measure(self, measure_time:int = 30, shutter_time: int = 2)-> List[float]:
		"""
		Arguments:
		shutter_time is interval between open/close events, in seconds
		measure_time is the duration of the entire measurement, in seconds

		Return value: list of floats [A,B]
		Where A and B are the gated measurements for each channel, in units of volts.
	
		This function computes gated datapoints as the mean of a shutter open period,
		subtracted by the mean of its flanking closed periods. It will always start
		and end a measurement with shutter-closed periods.

		Ex. If the measure_time is set to 7 seconds and the shutter_time to 1 second, then 
		there will be 3 shutter-open periods and 4 shutter-closed periods.

		_|-|_|-|_|-|_

		"""
		self.shutterA.close()
		self.shutterB.close()
		time.sleep(0.25)

		# The actual number of samples is taken as the ceiling of however many 
		# full open and closed periods it takes to complete the measurement
		self.shutter_samples = int(math.ceil(shutter_time/SAMPLE_TIME_S))
		# Number of shutter-open periods
		self.nSamples = int(math.floor(measure_time/(2*shutter_time)))
		# Number of shutter closed periods
		self.nDark = self.nSamples + 1
		# Raw samples are continous and include open and closed periods
		self.nRawSamples = self.shutter_samples*(self.nSamples + self.nDark)

		self.rawdataA = self.nRawSamples*[None]
		self.rawdataB = self.nRawSamples*[None]

		# Counters
		self._rsc = self._sc = self._errs = 0

		# Start logging incoming data
		GPIO.add_event_detect(self._adc._DRDY, GPIO.FALLING, callback=self._cb_adc_data_ready)

		self.t0 = time.time()
		try:
			sampleCount = 0

			# Start data acquisition loop
			while self._rsc < self.nRawSamples:

				# Do this once each time a full cycle (closed-open-closed) has completed:
				if (self._sc > sampleCount) and ((self._sc % 2)==0) and (self._sc > 2):
					print(f"\nMeasure: sample count = {self._sc}")

					self.dataA = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, SKIP_SAMPLES)
					print(f"Sensor A after {int(self._sc/2)} cycles: {FM_PER_V*mean(self.dataA):.4f} fM")
					print(f"Sensor A raw: {self.rawdataA[self._rsc-1]:.4f}")

					self.dataB = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, SKIP_SAMPLES)
					print(f"Sensor B after {int(self._sc/2)} cycles: {FM_PER_V*mean(self.dataB):.4f} fM")
					print(f"Sensor B raw: {self.rawdataB[self._rsc-1]:.4f}")

					start = time.time()

					self._display.displayResult(FM_PER_V*mean(self.dataA), FM_PER_V*mean(self.dataB))
					print(f"Display time: {time.time() - start}")
					sampleCount += 1

			self.dataA = self.gateTrace(self.rawdataA, self.shutter_samples, 10)
			self.dataB = self.gateTrace(self.rawdataB, self.shutter_samples, 10)

			self.resultA = mean(self.dataA)
			self.resultB = mean(self.dataB)
			self.semA = stdev(self.dataA)/math.sqrt(self.nSamples)
			self.semB = stdev(self.dataB)/math.sqrt(self.nSamples)

			print("")
			print(f"Sensor A final result: {FM_PER_V*self.resultA:.4f} fM +/- {FM_PER_V*self.semA:.4f} (s.e.m.) ")
			print(f"Sensor B final result: {FM_PER_V*self.resultB:.4f} fM +/- {FM_PER_V*self.semB:.4f} (s.e.m.) ")

			self._buzzer.buzz()
		
		except KeyboardInterrupt:
			self.writeToFile('Interrupted_')
		finally:
			self.t1 = time.time()

		print(f"\n{self._rsc} samples in {self.t1 - self.t0} seconds. Sample rate of {self._rsc / (self.t1 - self.t0)} Hz")
		print(f"{self._errs} CRC Errors encountered.")

		GPIO.remove_event_detect(self._adc._DRDY)

		return [self.resultA, self.resultB]

	def _cb_adc_data_ready(self, channel):
		# Callback function executed when data ready is asserted from ADC
		# The callback also opens and closes the shutter, in order to stay synchronized 
		# with the data readout.

		try:
			# Read sensor
			d = self._adc.read()

		except CRCError:
			errs += 1
			return
	
		if  self._rsc < self.nRawSamples:
			self.rawdataA[self._rsc] = d[0]
			self.rawdataB[self._rsc] = d[1]

			# Close shutters
			if self._rsc % (2*self.shutter_samples) == 0:
				try:
					self.shutterA.close()
					self.shutterB.close()
					time.sleep(SHUTTER_ACTUATION_TIME)
					self.shutterA.brake()
					self.shutterB.brake()


				except HBridgeFault:
					self._display.displayMessage('H-BRIDGE FAULT', True)

			# Open shutters
			elif self._rsc % self.shutter_samples == 0:
				try:
					self.shutterA.open()
					self.shutterB.open()
					time.sleep(SHUTTER_ACTUATION_TIME)
					self.shutterA.brake()
					self.shutterB.brake()

				except HBridgeFault:
					self._display.displayMessage('H-BRIDGE FAULT', True)

			self._rsc += 1
			self._sc = int(math.floor(self._rsc/self.shutter_samples))
		return

	def writeToFile(self, title):

		with open(title + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(self.nRawSamples):
				csvWriter.writerow((self.rawdataA[i], self.rawdataB[i]))

		with open(title + '_gated' + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(len(self.dataA)):
				csvWriter.writerow((self.dataA[i], self.dataB[i]))

	def gateTrace(self, rawData: List[float], gateSize: int, excludeSize: int = 0) -> List[float]:
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
			sample = mean(rawData[(i+excludeSize):i+(gateSize-1)])
			darkBefore = mean(rawData[(i-gateSize+excludeSize):(i-1)])
			darkAfter = mean(rawData[(i+gateSize+excludeSize):(i+2*gateSize - 1)])
			samples.append( sample - 0.5*(darkBefore + darkAfter))

		return samples 


	def measureUponButtonPress(self, iTime: int = 30, sTime: int = 2):
		startButton = BTN_3
		stopButton = BTN_2

		self._display.displayMessage("Press to measure", True)
		GPIO.setup(startButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(stopButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(stopButton, GPIO.FALLING, bouncetime=200)
		GPIO.add_event_detect(startButton, GPIO.FALLING, bouncetime=200)
		
		time.sleep(.2)

		try:
			while(GPIO.event_detected(stopButton) == False):
				print("Waiting for button press...")
				time.sleep(.1)
				if GPIO.event_detected(startButton):
					print('Button pressed')
					self._display.displayMessage("Measuring", True)
					self.measure(iTime)
		except KeyboardInterrupt:
			pass
		finally:
			GPIO.remove_event_detect(stopButton)
			GPIO.remove_event_detect(startButton)
			self._display.displayMessage("Goodbye!", True)
