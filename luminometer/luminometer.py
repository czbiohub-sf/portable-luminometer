#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time, math, csv, argparse
from datetime import datetime
import numpy as np
import os, json
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
		GPIO.setup(buzzPin, GPIO.OUT, initial=0)

	def buzz(self):
		GPIO.output(self._buzzPin, 1)
		time.sleep(BUZZ_S)
		GPIO.output(self._buzzPin, 0)

class LumiShutter():
	# Uses RPi BCM pinout
	# Written to operate a TI DRV8833 H-bridge chip.
	# Each instance of this class drives just one channel; create a second instance to drive two channels.

	def __init__(self, dirPin: int, pwmPin: int, faultPin: int, sleepPin: int):
		try:
			self._dirPin = int(dirPin)
			self._pwmPin = int(pwmPin)
			self._faultPin = int(faultPin)
			self._sleepPin = int(sleepPin)
		except TypeError:
			print('Pin value not convertible to integer!')
			raise

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._dirPin, GPIO.OUT, initial = 0)
		GPIO.setup(self._pwmPin, GPIO.OUT, initial = 0)

		#self._pwm = GPIO.PWM(self._pwmPin, SHT_PWM_FREQ)
		#self._pwm.start(0)

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

		self.rest()


	def actuate(self, action: str, driveTime: float = SHUTTER_ACTUATION_TIME):
		
		try:
			action = str(action)
		except TypeError:
			print("\naction must be a string!")
			return

		if not self._lock.locked():
			with self._lock:
				try:
					if action == 'open':
						self.driveOpen()
						time.sleep(driveTime)
						#self.holdOpen()
						self.rest()

					elif action == 'close':
						self.driveClosed()
						time.sleep(driveTime)
						#self.holdClosed()
						self.rest()

					else:
						print(f"\nShutter command not recognized!")
				except Exception as e:
					print(f"Shutter actuation error: {e}")
					self.rest()

		return

	def rest(self):
		try:
			self._pwm.stop()
		except:
			pass
		GPIO.output(self._dirPin, 0)
		GPIO.output(self._pwmPin, 0)


	def driveOpen(self):
		print(f"\nOpening shutter")
		GPIO.output(self._dirPin, 0)
		GPIO.output(self._pwmPin, 1)
		# self._pwm.stop()
		# self._pwm.start(SHUTTER_DRIVE_DR)
		#self._pwm.start(SHUTTER_DRIVE_DR)
		#self._pwm.ChangeDutyCycle(SHUTTER_DRIVE_DR)
	
	def driveClosed(self):
		print(f"\nClosing shutter")
		GPIO.output(self._dirPin, 1)
		GPIO.output(self._pwmPin, 0)
		# self._pwm.stop()
		# self._pwm.start(1-SHUTTER_DRIVE_DR)
		#self._pwm.start(1-SHUTTER_DRIVE_DR)
	
	def holdOpen(self):
		GPIO.output(self._dirPin, 1)
		try:
			self._pwm = GPIO.PWM(self._pwmPin, SHT_PWM_FREQ)
		except:
			pass
		self._pwm.start(1.0-SHUTTER_HOLD_DR)

	def holdClosed(self):
		GPIO.output(self._dirPin, 0)
		try:
			self._pwm = GPIO.PWM(self._pwmPin, SHT_PWM_FREQ)
		except:
			pass

		self._pwm.start(SHUTTER_HOLD_DR)

	def _faultDetected(self, channel):
		# Callback for handling an H-bridge fault pin event
		# Ref datasheet:
		# https://www.ti.com/lit/ds/symlink/drv8833.pdf?ts=1617084507643&ref_url=https%253A%252F%252Fwww.google.com%252F
		print('\nH-bridge fault detected!')
		raise HBridgeFault

	def __delete__(self):
		try:
			self._pwm.ChangeDutyCycle(0.0)
			self._pwm.stop()
		except:
			pass
		try:
			GPIO.output(self._dirPin, 0)
		except:
			pass


class Luminometer():

	def __init__(self):

		self._tempCoeffs = {}

		try:
			with open(CAL_PATH,'r') as json_file:
				data = json.load(json_file)
				self._tempCoeffs = data
		except Exception as exc:
			print(exc)
			print("Unable to load temp_coeffs file!")
			self._tempCoeffs["A"] = [SENSOR_A_DARK_V, SENSOR_A_CP_RATIO]
			self._tempCoeffs["B"] = [SENSOR_B_DARK_V, SENSOR_B_CP_RATIO]


		# Pin assignments
		self._btn1 = BTN_1
		self._btn2 = BTN_2
		self._btn3 = BTN_3
		self._FAN = FAN
		self._ADC_PWR_EN = ADC_PWR_EN
		self._PMIC_LBO = PMIC_LBO
		
		# Boolean internal variables
		self._powerOn = True
		self._measuring = False
		self._darkIsStored = False
		self._measurementIsDone = False

		# ADC Cyclic Redundancy Check - error counter
		self._crcErrs = 0

		# Set up channels for button pushes
		GPIO.setup(self._btn1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Set up low battery input
		GPIO.setup(self._PMIC_LBO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Set up sensor board power enable, and fan enable
		GPIO.setup(self._ADC_PWR_EN, GPIO.OUT, initial=1)
		GPIO.setup(self._FAN, GPIO.OUT, initial=1)

		# Add callback for button pushes
		GPIO.add_event_detect(self._btn1, GPIO.FALLING, callback=self._btn1_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn2, GPIO.FALLING, callback=self._btn2_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn3, GPIO.FALLING, callback=self._btn3_callback, bouncetime=200)

		self.display = LumiScreen()
		self.shutter = LumiShutter(SHT_1, SHT_PWM, SHT_FAULT, NSLEEP)
		self.shutter.rest()
		self.buzzer = LumiBuzzer(BUZZ)

		# Start up sensor chip
		try:
			self._adc = ADS131M08Reader()
			self._adc.setup_adc(SPI_CE, channels=[0,1])
			self._simulate = False
		except Exception as e:
			print("Error creating ADC reader!")
			print(e)
			self._simulate = True

		try: 
			self._adc.status_print()
		except Exception as e:
			print('Could not print ADC status!')
			print(e)

		# Start handling incoming ADC data
		if self._simulate:
			print("SIMULATION MODE: Starting timer callback")
			threading.Timer(SAMPLE_TIME_S, self._cb_adc_data_ready, args=(DRDY,)).start()
		else:
			GPIO.add_event_detect(self._adc._DRDY, GPIO.FALLING, callback=self._cb_adc_data_ready)

		# Create thread-safe queues for hardware jobs
		self._display_q = queue.Queue(maxsize=1)
		self._shutter_q = queue.Queue(maxsize=1)
		self._measure_q = queue.Queue(maxsize=1)
		self._measureLock = threading.Lock()

	def _btn1_callback(self, channel):
		# Handle presses to button 1

		startTime = time.perf_counter()
		nBeeps = 0
		powerOff = False
		print("Button 1 pressed")
		duration = 0

		# Monitor duration of button press
		while not GPIO.input(channel):
			time.sleep(0.1)
			duration = int(time.perf_counter() - startTime)
			if duration > nBeeps:
				print(f"Held for {duration} seconds")
				nBeeps += 1
				self.buzzer.buzz()

		if duration == BTN_1_HOLD_TO_POWERDOWN_S:
			print('POWER OFF')
			try:
				self._display_q.put((LumiMode.TITLE, 'POWER OFF'))
				time.sleep(5)
			except queue.Full:
				pass
			finally:
				self._powerOn = False

		elif duration == BTN_1_HOLD_TO_CALIBRATE_S:
			# Perform calibration
			if not self._measureLock.locked():
				try:
					self._measure_q.put_nowait((DEF_DARK_TIME,True))
				except queue.Full:
					pass
		
		return

	def _btn2_callback(self, channel):
		# Handle presses to button 2
		if not self._measuring:
			buzz1s = buzz2s = buzz3s = buzz4s = True
			exposure = 10

			startTime = time.perf_counter()
			while not GPIO.input(channel):
				duration = time.perf_counter() - startTime
				if (int(duration) == 1) and buzz1s:
					self.buzzer.buzz()
					buzz1s = False
					exposure = 30
				elif (int(duration)==2) and buzz2s:
					self.buzzer.buzz()
					buzz2s = False
					exposure = 60
				elif (int(duration)==3) and buzz3s:
					self.buzzer.buzz()
					buzz3s = False
					exposure = 300			
				elif (int(duration)==4) and buzz4s:
					self.buzzer.buzz()
					buzz4s = False
					exposure = 600

			try:
				if not self._measureLock.locked():
					self._measure_q.put_nowait((exposure, False))
			except queue.Full:
				print('\nAlready busy measuring')
	
	def _btn3_callback(self, channel):
		"""
		Handle presses to button 3
		Desired behavior:
		If the device is idle, pressing the button for any duration 
		will result in a measurement using auto-exposure.
		If the device is currently measuring, then we monitor for the 
		stop signal (a 3 second hold on the button)
		"""

		# A measurement is ongoing. Monitor for the stop condition
		if self._measuring:
			startTime = time.perf_counter()
			buzz3s = True
			while not GPIO.input(channel):
				time.sleep(0.2)
				duration = time.perf_counter() - startTime
				if duration > 3:
					if buzz3s:
						buzz3s = False
						self.buzzer.buzz()
						self._haltMeasurement = True
		
		# Add a measurement to the queue
		else:
			try:
				if not self._measureLock.locked():
					self._measure_q.put_nowait((0,False))
			except queue.Full:
				pass

	def measure(self, \
		measure_time: int = 30, \
		isCalibration: bool = False):
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
				print("Starting measurement")
				
				# Confirm to user that a calibration is being performed
				if isCalibration:
					try:
						self._display_q.put((LumiMode.TITLE, 'CALIBRATION'))
					except queue.Full:
						pass

				# Close shutters
				try:
					self._shutter_q.put('close')
				except queue.Full:
					pass

				self._resetBuffers(measure_time)

				t0 = time.perf_counter()

				try:
					self._measuring = True

					# Keeps track of the overall measurement duration
					sampleCount = 0

					# Start data acquisition loop
					while self._loopCondition(measure_time):

						# Do this once each time a full cycle (closed-open-closed) has completed:
						if (self._sc > sampleCount) and ((self._sc % 2)==0) and (self._sc > 2):
							print(f"\nMeasure: sample count = {self._sc}")

							# Gate traces 
							self.dataA, _ = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, "A", False)
							self.dataB, _ = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, "B", False)
							
							# Recalculate mean
							self.resultA = mean(self.dataA)
							self.resultB = mean(self.dataB)							

							print(f"Sensor A after {int(self._sc/2)} cycles: {RLU_PER_V*self.resultA:.2f}")
							print(f"Sensor A raw: {self.rawdataA[self._rsc-1]:.8f}")
							print(f"Sensor B after {int(self._sc/2)} cycles: {RLU_PER_V*self.resultB:.2f}")
							print(f"Sensor B raw: {self.rawdataB[self._rsc-1]:.8f}")

							# Can't compute stdev unless there are >3 shutter-open periods _|-|_|-|_|-|_
							if self._sc > 5:
								self.semA = stdev(self.dataA)/math.sqrt(float(len(self.dataA)))
								self.semB = stdev(self.dataB)/math.sqrt(float(len(self.dataB)))

							self._duration_s = time.perf_counter() - t0

							self._updateDisplayResult()

							sampleCount += 1

					# Final: gate traces. If calibration, do the fit and write the file
					self.dataA, rawDownsampledA = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, "A", isCalibration)
					self.dataB, rawDownsampledB = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, "B", isCalibration)	

					# Final result is the mean of all the gated shutter-open periods
					self.resultA = mean(self.dataA)
					self.resultB = mean(self.dataB)
					self.semA = stdev(self.dataA)/math.sqrt(float(len(self.dataA)))
					self.semB = stdev(self.dataB)/math.sqrt(float(len(self.dataB)))

					# If doing a dark calibration, then store the result
					if isCalibration:
						fitParamsA = np.polyfit(rawDownsampledA, self.dataA, 1, full=False)
						fitParamsB = np.polyfit(rawDownsampledB, self.dataB, 1, full=False)
						
						# Convert fit parameters to V_dark at zero temperature
						offsetA = -fitParamsA[1]/fitParams[0]
						crA = fitParamsA[0]
						self._tempCoeffs["A"] = [offsetA, crA]
						offsetB = -fitParamsB[1]/fitParamsB[0]
						crB = fitParamsA[0]
						self._tempCoeffs["B"] = [offsetB, crB]


						print(f"Offset A: {offsetA}")
						print(f"Coupling coeff A: {crA}")						
						print(f"Offset B: {OffsetB}")
						print(f"Coupling coeff B: {crB}")

						with open(CAL_PATH,'w') as outfile:
							json.dump(self._tempCoeffs, outfile)

					print(f"\nSensor A final result: {RLU_PER_V*self.resultA:.2f} +/- {RLU_PER_V*self.semA:.2f} (s.e.m.) ")
					print(f"\nSensor B final result: {RLU_PER_V*self.resultB:.2f} +/- {RLU_PER_V*self.semB:.2f} (s.e.m.) ")
					print(f"\n{self._rsc} samples in {time.perf_counter() - t0} seconds. Sample rate of {self._rsc / (time.perf_counter() - t0)} Hz")
					print(f"{self._crcErrs} CRC Errors encountered.")

					self.writeToFile()
					self.buzzer.buzz()
				
				except KeyboardInterrupt as exc:
					#self.writeToFile('Interrupted_')
					print("Keyboard interrupted measurement")
				finally:
					self._measuring = False
					self._measurementIsDone = True
					self.shutter.rest()
					time.sleep(5)
					self._updateDisplayResult(True)

		return


	def _loopCondition(self, exposure:int) -> bool:
		if exposure > 0:
			result = (self._rsc < self.nRawSamples) and (self._haltMeasurement == False)
			return result

		# Auto-exposure
		else:

			result = \
					((self._duration_s < MAX_EXPOSURE) and \
					(self._haltMeasurement == False) and \
					((abs(self.resultB) / self.semB)) < MIN_SNR) or \
					((self._sc) < MIN_PERIODS)
			return result

	def _cb_adc_data_ready(self, channel):
		# Callback function executed when data ready is asserted from ADC
		# The callback also queues the shutter actions, in order to stay synchronized 
		# with the data readout.

		if self._simulate:
			# Simulation mode
			d = [0.0, 0.0]
			threading.Timer(SAMPLE_TIME_S, self._cb_adc_data_ready, args=(DRDY,)).start()
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
			self._sc = int(self._rsc/self.shutter_samples)
		return		

	def _updateDisplayResult(self, wait: bool = False):
		# Update display with intermediate results
		args = (\
				LumiMode.RESULT, \
				self._darkIsStored,\
				self._measurementIsDone,\
				RLU_PER_V*mean(self.dataA),\
				RLU_PER_V*self.semA,\
				RLU_PER_V*mean(self.dataB),\
				RLU_PER_V*self.semB,\
				self._duration_s)
		try:
			if wait:
				# Ensure the final result is displayed
				while self._display_q.full():
					pass
				self._display_q.put(args)
			else:
				self._display_q.put_nowait(args)
		except queue.Full:
			print('\nDisplay queue full. Could not display result')

	def _resetBuffers(self, measure_time: int):

			self.dataA = [0.0]
			self.dataB = [0.0]
			self.semA = float('inf')
			self.semB = float('inf')
			self.resultA = 0.0
			self.resultB = 0.0
			self._measurementIsDone = False
			self._haltMeasurement = False

			# The actual number of samples is taken as the ceiling of however many 
			# full open and closed periods it takes to complete the measurement
			self.shutter_samples = int(math.ceil(SHUTTER_PERIOD/SAMPLE_TIME_S))

			# Number of shutter-open periods
			if measure_time > 0:
				self.nSamples = int(measure_time/(2*SHUTTER_PERIOD))
			else:
				self.nSamples = DEF_AUTO_MAX_DURATION

			# Number of shutter closed periods
			self.nDark = self.nSamples + 1

			# Raw samples are continous and include open and closed periods
			self.nRawSamples = self.shutter_samples*(self.nSamples + self.nDark)

			self.rawdataA = self.nRawSamples*[None]
			self.rawdataB = self.nRawSamples*[None]
			self._duration_s = 0.0

			# Counters
			self._rsc = self._sc = self._crcErrs = 0

	def writeToFile(self):
		now = datetime.now()
		dt_string = now.strftime("%Y-%m-%d-%H-%M-%S")
		title = dt_string
		with open(title + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(self.nRawSamples):
				csvWriter.writerow((self.rawdataA[i], self.rawdataB[i]))

		with open(title + '_gated' + '.csv', 'w', newline='') as csvFile:
			csvWriter = csv.writer(csvFile)
			for i in range(len(self.dataA)):
				csvWriter.writerow((self.dataA[i], self.dataB[i]))

	def gateTrace(self, rawData: List[float], gateSize: int, channel: str, isCalibration: bool = False) -> List[float]:
		"""
		Helper method that computes the mean of each even chunk of data, subtracted by the mean of the flanking odd
		chunks of data. The chunk size is specified by gateSize, and the total size of the rawData should be an odd
		multiple of gateSize, so that every even chunk has two flanking odd chunks.

		The function will disregard raw data that does not consist of a complete odd multiple of the gateSize.

		Here, we also correct for residual thermal offset. This effect manifests as a difference in signal between shutter-
		open and shutter-closed stages regardless of sample present. The effect is not 100% understood, but one potential
		root cause could be that the SiPM sensor itself emits light in direct proportion to its dark current (it acts like an LED). 
		There is some small amount of light that reflects back on itself (more or less, depending on shutter state), which it then detects.
		The effect seems to be corrigible by subtracting a linear fit from the raw dark current of the sensor.

		Inputs:
			rawData: List of float values consisting of raw sensor reads in a time-series.
			gateSize: Integer depicting the number of raw sensor reads in each shutter-open or shutter-closed state.
		"""

		nPeriods = int(len(rawData) / gateSize)

		if nPeriods < 3:
			print("Raw data size must be greater than three times gateSize!")
			return [0.0]

		# Process only up the last odd-numbered period
		if nPeriods % 2 == 0:
			nPeriods = nPeriods -1

		samples = []
		rawDownsampled = []

		for i in range(gateSize, gateSize*nPeriods, 2*gateSize):
			sample = mean(rawData[(i+SKIP_SAMPLES):i+(gateSize-1)])
			darkBefore = mean(rawData[(i-gateSize+SKIP_SAMPLES):(i-1)])
			darkAfter = mean(rawData[(i+gateSize+SKIP_SAMPLES):(i+2*gateSize - 1)])
			darkMean = 0.5*(darkBefore + darkAfter)

			rawDownsampled.append(darkMean)
			gatedSample = sample - darkMean

			if isCalibration:
				samples.append(gatedSample)
			else:
				samples.append(self.correctTemperature(gatedSample, darkMean, self._tempCoeffs[channel]))

		return samples, rawDownsampled


	def correctTemperature(self, gatedIn: float, darkMeanIn: float, tempCoeffs: List[float]) -> float:
		return gatedIn - tempCoeffs[1]*(darkMeanIn - tempCoeffs[0])

	def run(self):

		self.shutter.rest()

		try:
			with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:

				# Start a future for thread to submit work through the queue
				future_result = { \
					executor.submit(Luminometer.shutter.actuate, 'close'): 'SHUTTER CLOSED', \
					}

				# Display to the user that the system is started and ready
				self._display_q.put_nowait((LumiMode.READY, self._darkIsStored))


				print('\nReady and waiting for button pushes...')

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

						future_result[executor.submit(self.measure, *measureType)] = f"Exposure = {measureType[0]}, Dark = {measureType[1]}"

					# Shutter queue has size 1 and will not add additional items to the queue
					while not self._shutter_q.empty():

						# Fetch an action from the queue
						try:
							action = self._shutter_q.get_nowait()
						except queue.Empty:
							pass

						# Submit shutter actions
						future_result[executor.submit(self.shutter.actuate, action)] = "Shutter: " + action

					# Display queue has size 1 and will not add additional items to the queue
					# If there is an incoming message, start a new future
					while not self._display_q.empty():

						# Fetch a job from the queue
						try:
							message = self._display_q.get_nowait()
						except queue.Empty:
							pass

						# Start the load operation and mark the future with its URL
						future_result[executor.submit(self.display.parser, *message)] = "Message displayed: " + repr(message[0])

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
	Luminometer = Luminometer()
	try:
		Luminometer.run()
	except Exception as exc:
		print(f'Luminometer encountered exception: {exc}')
	finally:
		GPIO.cleanup()
		del(Luminometer)
		
		# Power down system
		os.system('sudo poweroff')


