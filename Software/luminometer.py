#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time
import math
import csv
import argparse
import RPi.GPIO as GPIO
from typing import List

from consts import *
from ads131m08_reader import ADS131M08Reader, bytes_to_readable, CRCError

# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050

# Device user input pushbuttons, BCM pins
BTN_1 = 3
BTN_2 = 26
BTN_3 = 19

AIN1 = 16
AIN2 = 13
BIN1 = 5
BIN2 = 6

NSLEEP = 1
NFAULT = 0

CE = 1

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
			pass

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._fwdPin, GPIO.OUT, initial = 0)
		GPIO.setup(self._revPin, GPIO.OUT, initial = 0)
		GPIO.setup(self._sleepPin, GPIO.OUT, initial = 1)
		GPIO.setup(self._faultPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		
		self.readFault()

	def open(self):
		if not self.readFault():
			GPIO.output([self._fwdPin,self._revPin], (1,0))

	def close(self):
		if not self.readFault():
			GPIO.output([self._fwdPin, self._revPin], (0,1))

	def rest(self):
		GPIO.output([self._fwdPin, self._revPin], (0,0))
		self.readFault()

	def brake(self):
		GPIO.output([self._fwdPin, self._revPin], (1,1))
		self.readFault()

	def readFault(self):
		# Returns true if there is a fault
		if GPIO.input(self._faultPin):
			return False
		else:
			print('H-bridge fault detected!')
			return True

class Luminometer():

	def __init__(self, shutterA, shutterB):

		self._adc = ADS131M08Reader()
		self._adc.setup_adc(CE, channels=[0,1])

		self.shutterA = shutterA
		self.shutterB = shutterB

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

	def measure(self, measure_time=11, shutter_time=1)-> List[float]:
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
		
		# The actual number of samples is taken as the ceiling of however many 
		# full open and closed periods it takes to complete the measurement
		self.shutter_samples = int(math.ceil(shutter_time/SAMPLE_TIME_S))
		self.nSamples = int(math.floor(measure_time/(2*shutter_time)))
		self.nDark = self.nSamples + 1

		# Raw samples are continous and include open and closed periods
		self.nRawSamples = self.shutter_samples*(self.nSamples + self.nDark)

		self.rawdataA = self.rawDataB = self.nRawSamples*[None]
		self.dataA = self.dataB = (self.nSamples+self.nDark)*[None]

		# Counters
		self._rsc = self._sc = self._errs = 0

		# Start logging incoming data
		GPIO.add_event_detect(self._adc._DRDY, GPIO.FALLING, callback=self._cb)

		self.t0 = time.time()
		try:
			while self._rsc < self.nRawSamples:
				pass
		except KeyboardInterrupt:
			pass
		finally:
			self.t1 = time.time()

		print(f"\n{self._rsc} samples in {self.t1 - self.t0} seconds. Sample rate of {self._rsc / (self.t1 - self.t0)} Hz")
		print(f"{self._errs} CRC Errors encountered.")

	def _cb(self, channel):
		# Callback function executed when data ready is asserted from ADC
		
		# Read sensor
		d = self._adc.read()
		
		if (self._rsc + 1) <= self.nRawSamples:
			self.rawdataA[self._rsc] = d[0]
			self.rawDataB[self._rsc] = d[1]
		
			try:
				# Close shutters
				if self._rsc % (2*self.shutter_samples) == 0:
					#self.shutterA.close()
					self.shutterB.close()

				# Open shutters
				elif self._rsc % self.shutter_samples == 0:
					#self.shutterA.open()
					self.shutterB.open()

			except CRCError:
				errs += 1
				return

			self._rsc += 1
			self._sc = int(math.floor(self._rsc/self.shutter_samples))

			print(f"CH0: {d[0]} \t CH1: {d[1]}")

	def writeToFile(self, title):

		with open(title + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(self.nRawSamples):
				csvWriter.writerow([self.rawdataA[i], self.rawDataB[i]])



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

	Luminometer = Luminometer(shutterA, shutterB)

	Luminometer.measure(integrationTime_seconds, shutterTime)
	Luminometer.writeToFile(title)
	GPIO.cleanup()
