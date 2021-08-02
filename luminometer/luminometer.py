#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time, math, csv, argparse, logging
from datetime import datetime
import numpy as np
import os, json
import RPi.GPIO as GPIO
import pigpio
import concurrent.futures
import threading
import queue
from typing import List
from statistics import mean, stdev

from adc_constants import *
from luminometer_constants import *
from lumiscreen import LumiScreen, LumiMode
from ads131m08_reader import ADS131M08Reader, bytes_to_readable, CRCError
from menu import Menu, MenuStates

############################## SET UP MEASUREMENT AND LOGGING DIRECTORIES ##############################
LOG_OUTPUT_DIR = "/home/pi/luminometer-logs/"
MEASUREMENT_OUTPUT_DIR = "/home/pi/measurements/"
if not os.path.exists(LOG_OUTPUT_DIR):
	os.mkdir(LOG_OUTPUT_DIR)
if not os.path.exists(MEASUREMENT_OUTPUT_DIR):
	os.mkdir(MEASUREMENT_OUTPUT_DIR)

############################## SETUP LOGGER ##############################
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_location = os.path.join(LOG_OUTPUT_DIR, "luminometer.log")

# Set up logging to a file
file_handler = logging.FileHandler(log_location)
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s: %(message)s", "%Y-%m-%d-%H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Set up logging to the console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

class HBridgeFault(Exception):
	logger.exception("\nH-bridge fault detected!")
	pass

class LumiBuzzer():
	def __init__(self, buzzPin: int):
		try:
			self._buzzPin = int(buzzPin)
		except TypeError:
			logger.exception("Pin value not convertible to integer!")
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
			logger.error("Pin value not convertible to integer!")
			raise

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._dirPin, GPIO.OUT, initial = 0)
		# GPIO.setup(self._pwmPin, GPIO.OUT, initial = 0)

		# self._pwm = GPIO.PWM(self._pwmPin, SHT_PWM_FREQ)
		# self._pwm.start(0)
		self._pi = pigpio.pi()
		self._pi.hardware_PWM(self._pwmPin, 0, 0)
		self.hbridge_err = "OK"

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
		logger.info("Successfully instantiated LumiShutter.")

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
						self.holdOpen()

					elif action == 'close':
						self.driveClosed()
						time.sleep(driveTime)
						self.holdClosed()

					else:
						print(f"\nShutter command not recognized!")
				except Exception as e:
					logger.exception(f"Shutter actuation error: {e}")
					self.rest()

		return

	def rest(self):
		try:
			GPIO.output(self._dirPin, 0)
			logger.info("Turning off PWM, resting.")
			self._pi.hardware_PWM(self._pwmPin, 0, 0)
		except:
			pass


	def driveOpen(self):
		logger.info(f"\nOpening shutter")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, SHUTTER_DRIVE_DR)
		GPIO.output(self._dirPin, 0)
	
	def driveClosed(self):
		logger.debug(f"Closing shutter")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, 0)
		GPIO.output(self._dirPin, 1)
	
	def holdOpen(self):
		logger.debug("Holding open.")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, SHUTTER_HOLD_DR)
		GPIO.output(self._dirPin, 0)

	def holdClosed(self):
		logger.debug("Holding closed.")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, 1000000 - SHUTTER_HOLD_DR)
		GPIO.output(self._dirPin, 1)

	def _faultDetected(self, channel):
		# Callback for handling an H-bridge fault pin event
		# Ref datasheet:
		# https://www.ti.com/lit/ds/symlink/drv8833.pdf?ts=1617084507643&ref_url=https%253A%252F%252Fwww.google.com%252F
		self.hbridge_err = "ERR"
		raise HBridgeFault

	def __delete__(self):
		try:
			self._pi.hardware_PWM(self._pwmPin, 0, 0)
		except:
			pass
		try:
			GPIO.output(self._dirPin, 0)
		except:
			pass

class Luminometer():

	def __init__(self):

		self.state = MenuStates.MAIN_MENU
		self.measurementMode = ""
		self.target_time = 0
		self.selected_calibration = ""
		self._duration_s = 0
		self.resultA = 0
		self.semA = 0
		self.resultB = 0
		self.semB = 0
		self.diag_vals = {
			"batt": "OK",
			"34V": "OK",
			"pbias": "OK",
			"num_CRC_errs": 0,
			"hbridge_err": "OK",
		}
		self.adc_vals = 0
		self.screen_settled = True
		
		# Get last selected calibration
		try:
			with open(LAST_CAL) as json_file:
				data = json.load(json_file)
				self.selected_calibration = data
				logger.info(f"Previously used calibration file found. Using {self.selected_calibration}.")
		except:
			logger.warning("Could not open last_chosen_cal.json, defaulting to standard calibration.")
			self.selected_calibration = "Default"

		self._tempCoeffs = {}
		try:
			if self.selected_calibration == "A":
				PATH = CUSTOM_CAL_A_PATH
			else:
				PATH = STANDARD_CAL_PATH

			with open(PATH,'r') as json_file:
				data = json.load(json_file)
				self._tempCoeffs = data
				logger.info(f"Successfully loaded {self.selected_calibration} file.")
		except Exception as exc:
			logger.exception(f"Unable to load calibration {self.selected_calibration} temp_coeffs file!")
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

		# TODO, Get battery status dynamically
		self.batt_status = "OK"
		self.calA = " - NOT SET"
		logger.info("Checking to see if custom calibration file exists.")
		if os.path.isfile(CUSTOM_CAL_A_PATH):
			logger.info("Custom calibration file exists.")
			self.calA = ""

		logger.info("Instantiating display, shutter, and buzzer.")
		self.display = Menu(self.selected_calibration, self.batt_status)
		# logger.info("Successfully instantiated Menu display.")
		try:
			self.shutter = LumiShutter(SHT_1, SHT_PWM, SHT_FAULT, NSLEEP)
			self.shutter.rest()
			logger.info("Successfully instantiated LumiShutter.")
		except Exception as e:
			logger.exception("Error instantiating LumiShutter!")
		try:
			self.buzzer = LumiBuzzer(BUZZ)
			logger.info("Successfully instantiated LumiBuzzer.")
		except Exception as e:
			logger.exception("Error instantiating LumiBuzzer!")

		# Start up sensor chip
		try:
			logger.info("Starting up sensor chip.")
			self._adc = ADS131M08Reader()
			self._adc.setup_adc(SPI_CE, channels=[0,1])
			self._simulate = False
		except Exception as e:
			logger.exception("Error creating ADC reader!")
			self._simulate = True

		try: 
			logger.info("Printing ADC status.")
			self._adc.status_print()
		except Exception as e:
			logger.exception('Could not print ADC status!')

		# Start handling incoming ADC data
		if self._simulate:
			logger.info("SIMULATION MODE: Starting timer callback")
			threading.Timer(SAMPLE_TIME_S, self._cb_adc_data_ready, args=(DRDY,)).start()
		else:
			GPIO.add_event_detect(self._adc._DRDY, GPIO.FALLING, callback=self._cb_adc_data_ready)

		# Create thread-safe queues for hardware jobs
		logger.info("Creating display, shutter, and measure queues.")
		self._display_q = queue.Queue(maxsize=1)
		self._shutter_q = queue.Queue(maxsize=1)
		self._measure_q = queue.Queue(maxsize=1)
		logger.info("Successfully created queues.")
		self._measureLock = threading.Lock()

		# Add callback for button pushes
		logger.info("Setting up button callbacks.")
		GPIO.add_event_detect(self._btn1, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn2, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn3, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)

		self.set_state(MenuStates.MAIN_MENU)
		logger.info("Successfully instantiated Luminometer.")

	def set_state(self, state: MenuStates):
		# Check for a low battery
		if not GPIO.input(self._PMIC_LBO):
			self.batt_status = "LO"
		
		# If transitioning to main menu or status, update the diag and adc values
		try:
			if state == MenuStates.MAIN_MENU or state == MenuStates.STATUS_MENU:
				# TODO self.adc_vals = pauls_function()
				# self.adc_vals = averageNMeasurements()
				self.diag_vals["batt"] = self.batt_status
				self.diag_vals["34V"] = self.adc_vals[4]
				self.diag_vals["pbias"] = self.adc_vals[3]
				self.diag_vals["num_CRC_errs"] = self._crcErrs
				self.diag_vals["hbridge_err"] = self.shutter.hbridge_err
		except:
			logger.exception("Error setting adc/diag vals")

		display_kwargs = {
			"state": state,
			"battery_status": self.batt_status,
			"selected_calibration": self.selected_calibration,
			"calA": self.calA,
			"measurementMode": self.measurementMode,
			"time_elapsed": self._duration_s,
			"target_time": self.target_time,
			"_measurementIsDone": self._measurementIsDone,
			"resultA": self.resultA,
			"semA": self.semA,
			"resultB": self.resultB,
			"semB": self.semB,
			"diag_vals": self.diag_vals,
			"adc_vals": self.adc_vals,
		}
		try:
			if self.screen_settled:
				self.buzzer.buzz()
				logger.info(f"Current state: {self.state}")
				logger.info(f"Moving to: {state}")
				self.screen_settled = False
				self._display_q.put(display_kwargs)
				self.state = state
			else:
				logger.info("Screen not yet settled.")
		except queue.Full:
			logger.info("Display queue full.")
			pass

	def unified_callback(self, channel):

		if not self.screen_settled and not self._measuring:
			return

		button = None
		if channel == BTN_1:
			button = 1
		elif channel == BTN_2:
			button = 2
		elif channel == BTN_3:
			button = 3

		# Get duration of button hold
		buzz1s = buzz2s = buzz3s = buzz4s = buzz5s = True
		duration = 0
		startTime = time.perf_counter()
		while not GPIO.input(channel):
			duration = time.perf_counter() - startTime
			if (int(duration) == 1) and buzz1s:
				self.buzzer.buzz()
				buzz1s = False
				logger.info(f"Button {button} held for 1 second.")
			elif (int(duration)==2) and buzz2s:
				self.buzzer.buzz()
				buzz2s = False
				logger.info(f"Button {button} held for 2 seconds.")
			elif (int(duration)==3) and buzz3s:
				self.buzzer.buzz()
				buzz3s = False
				logger.info(f"Button {button} held for 3 seconds.")			
			elif (int(duration)==4) and buzz4s:
				self.buzzer.buzz()
				buzz4s = False
				logger.info(f"Button {button} held for 4 seconds.")
			elif (int(duration)==5) and buzz5s:
				self.buzzer.buzz()
				buzz5s = False
				logger.info(f"Button {button} held for 5 seconds.")

		if button == 1:
			self.btn1_transition_logic(duration)
		elif button == 2:
			self.btn2_transition_logic(duration)
		elif button == 3:
			self.btn3_transition_logic(duration)

	def btn1_transition_logic(self, duration):
		'''This is the bottom button
		'''

		logger.info("Button 1 (bottom) pressed.")
		nextState = None

		# Power off if bottom button held for 5s
		if int(duration) == 5:
			nextState = MenuStates.POWER_OFF
			logger.info('POWER OFF')
			self._haltMeasurement = True
			self._powerOn = False

		elif self.state == MenuStates.MAIN_MENU:
			nextState = MenuStates.CALIBRATION_MENU

		elif self.state == MenuStates.MEASUREMENT_MENU:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.SHOW_FINAL_MEASUREMENT:
			nextState = MenuStates.MEASUREMENT_MENU

		elif self.state == MenuStates.STATUS_MENU:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CALIBRATION_MENU:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CONFIRM_CALIBRATION:
			nextState = MenuStates.MAIN_MENU

		if nextState != None:
			self.set_state(nextState)

	def btn2_transition_logic(self, duration):
		'''This is the MIDDLE button
		'''

		logger.info(f"Button 2 (middle) pressed. {self.state}")
		nextState = None

		if self.state == MenuStates.MAIN_MENU:
			nextState = MenuStates.STATUS_MENU

		elif self.state == MenuStates.MEASUREMENT_MENU:
			
			# Perform timed measurement
			if not self._measuring:
				exposure = 10
				
				if int(duration) == 1:
					exposure = 30
				elif int(duration) == 2:
					exposure = 60
				elif int(duration) == 3:
					exposure = 300
				elif int(duration) == 4:
					exposure = 600
				self.target_time = exposure
		
				try:
					if not self._measureLock.locked():
						self._measure_q.put_nowait((exposure, False))
				except queue.Full:
					logger.info('\nAlready busy measuring')

				self._duration_s = 0
				self.measurementMode = "TIMED"
				nextState = MenuStates.MEASUREMENT_IN_PROGRESS

		elif self.state == MenuStates.CALIBRATION_MENU:
			# Switch to custom calibration A and return to main
			# or begin new calibration if held for 5 seconds
			
			calibrate = False

			if int(duration) == 5:
				calibrate = True
			
			# If held for 5s, prompt user to confirm they want to calibrate, otherwise load default
			if calibrate:
				logger.info("Button 2 held for 5 seconds, move to confirm calibration with user.")
				nextState = MenuStates.CONFIRM_CALIBRATION
			else:
				# Get constants
				logger.info("Attempt to load existing custom calibration.")
				try:
					if os.path.isfile(CUSTOM_CAL_A_PATH):
						logger.info("Found custom calibration file.")
						with open(CUSTOM_CAL_A_PATH,'r') as json_file:
							data = json.load(json_file)
							self._tempCoeffs = data
						
						# Set custom as last chosen calibration
						self.selected_calibration = "Custom"
						with open(LAST_CAL, "w") as json_file:
							json.dump(self.selected_calibration, json_file)
						self.display.set_selected_calibration(self.selected_calibration)
						nextState = MenuStates.MAIN_MENU
					else:
						logger.info("No custom calibration found. No changes made.")
						nextState = MenuStates.MAIN_MENU
				except Exception as e:
					print("Error encountered while opening custom calibration")
					nextState = MenuStates.MAIN_MENU

		if nextState != None:
			self.set_state(nextState)
		
	
	def btn3_transition_logic(self, duration):
		'''This is the TOP button
		'''

		logger.info("Button 3 (top) pressed.")
		nextState = None

		if self.state == MenuStates.MAIN_MENU:
			nextState = MenuStates.MEASUREMENT_MENU

		elif self.state == MenuStates.MEASUREMENT_MENU:
			nextState = MenuStates.MEASUREMENT_IN_PROGRESS
			self.measurementMode = "AUTO"
			self._duration_s = 0
			self.target_time = None

			exposure = 0
			try:
				if not self._measureLock.locked():
					self._measure_q.put_nowait((exposure, False))
			except queue.Full:
				logger.info('\nAlready busy measuring')

		elif self.state == MenuStates.MEASUREMENT_IN_PROGRESS:
			# Measurement in progress
			# Abort and return to measurement menu if top button held for 3s
			if duration >= 3:
				logger.info(f"Button 3 held for 3 seconds - halting measurement.")
				self.buzzer.buzz()
				self._haltMeasurement = True
				nextState = MenuStates.MEASUREMENT_MENU
				while not self.screen_settled or self._measuring:
					pass
		
		elif self.state == MenuStates.CALIBRATION_MENU:
			# Switch to standard calibration and return to main
			self.selected_calibration = "Default"
			self.display.set_selected_calibration(self.selected_calibration)

			# Get constants
			with open(STANDARD_CAL_PATH,'r') as json_file:
				data = json.load(json_file)
				self._tempCoeffs = data
			
			# Set default as last chosen calibration
			with open(LAST_CAL, "w") as json_file:
				json.dump(self.selected_calibration, json_file)
				
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CONFIRM_CALIBRATION:
			# Perform calibration
			if not self._measureLock.locked():
				try:
					logger.info("Performing calibration.")
					self._measure_q.put_nowait((DEF_DARK_TIME,True))
				except queue.Full:
					pass
		
		if nextState != None:
			self.set_state(nextState)

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
				logger.info("Starting measurement")

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
							logger.info(f"Measure: sample count = {self._sc}")

							# Gate traces 
							self.dataA, _ = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, "A", False)
							self.dataB, _ = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, "B", False)
							
							# Recalculate mean
							self.resultA = mean(self.dataA)
							self.resultB = mean(self.dataB)							

							logger.info(f"Sensor A after {int(self._sc/2)} cycles: {RLU_PER_V*self.resultA:.2f}")
							logger.info(f"Sensor A raw: {self.rawdataA[self._rsc-1]:.8f}")
							logger.info(f"Sensor B after {int(self._sc/2)} cycles: {RLU_PER_V*self.resultB:.2f}")
							logger.info(f"Sensor B raw: {self.rawdataB[self._rsc-1]:.8f}")

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

					# If doing a calibration, then store the result
					if isCalibration:
						fitParamsA = np.polyfit(rawDownsampledA, self.dataA, 1, full=False)
						fitParamsB = np.polyfit(rawDownsampledB, self.dataB, 1, full=False)
						
						# Convert fit parameters to V_dark at zero temperature
						offsetA = -fitParamsA[1]/fitParamsA[0]
						crA = fitParamsA[0]
						self._tempCoeffs["A"] = [offsetA, crA]
						offsetB = -fitParamsB[1]/fitParamsB[0]
						crB = fitParamsB[0]
						self._tempCoeffs["B"] = [offsetB, crB]

						logger.debug(f"Offset A: {offsetA}")
						logger.debug(f"Coupling coeff A: {crA}")						
						logger.debug(f"Offset B: {offsetB}")
						logger.debug(f"Coupling coeff B: {crB}")

						with open(CUSTOM_CAL_A_PATH,'w') as outfile:
							json.dump(self._tempCoeffs, outfile)

					logger.info(f"\nSensor A final result: {RLU_PER_V*self.resultA:.2f} +/- {RLU_PER_V*self.semA:.2f} (s.e.m.) ")
					logger.info(f"\nSensor B final result: {RLU_PER_V*self.resultB:.2f} +/- {RLU_PER_V*self.semB:.2f} (s.e.m.) ")
					logger.info(f"\n{self._rsc} samples in {time.perf_counter() - t0} seconds. Sample rate of {self._rsc / (time.perf_counter() - t0)} Hz")
					logger.info(f"{self._crcErrs} CRC Errors encountered.")

					self.writeToFile()
					self.buzzer.buzz()
				
				except KeyboardInterrupt as exc:
					#self.writeToFile('Interrupted_')
					logger.error("Keyboard interrupted measurement")
				finally:
					self._measuring = False
					self._measurementIsDone = True
					self._duration_s = time.perf_counter() - t0
					self.shutter.rest()
					if not self._haltMeasurement:
						self._updateDisplayResult(True)
					time.sleep(5)

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
					((self._sc) < MIN_PERIODS and self._haltMeasurement == False)
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
				self.adc_vals = d

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
		logger.debug("Updating intermediate results.")
		self.resultA = RLU_PER_V*mean(self.dataA)+ADD_OFFSET_RLU
		self.semA = RLU_PER_V*self.semA
		self.resultB = RLU_PER_V*mean(self.dataB)+ADD_OFFSET_RLU
		self.semB = RLU_PER_V*self.semB
		try:
			if wait:
				# Ensure the final result is displayed
				logger.debug("Waiting to display final...")
				while not self.screen_settled:
					pass
				logger.debug("Setting final measurement state")
				self.set_state(MenuStates.SHOW_FINAL_MEASUREMENT)
				self._duration_s = 0
			else:
				if self.screen_settled:
					logger.debug("Setting measurement in progress state")
					self.set_state(MenuStates.MEASUREMENT_IN_PROGRESS)
		except queue.Full:
			logger.error('\nDisplay queue full. Could not display result')

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
		title = os.path.join(MEASUREMENT_OUTPUT_DIR, dt_string)
		try:
			logger.info(f"Attepmting to save to {title}")
			with open(title + '.csv', 'w', newline='') as csvFile:
				csvWriter = csv.writer(csvFile)
				for i in range(self.nRawSamples):
					csvWriter.writerow((self.rawdataA[i], self.rawdataB[i]))

			with open(title + '_gated' + '.csv', 'w', newline='') as csvFile:
				csvWriter = csv.writer(csvFile)
				for i in range(len(self.dataA)):
					csvWriter.writerow((self.dataA[i], self.dataB[i]))
			logger.info("File successfully saved.")
		except:
			logger.exception("Could not save measurement to file.")

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
			logger.error("Raw data size must be greater than three times gateSize!")
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
				# self._display_q.put_nowait((LumiMode.READY, self._darkIsStored))


				logger.info('\nReady and waiting for button pushes...')

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
							kwargs = self._display_q.get_nowait()
						except queue.Empty:
							pass

						# Start the load operation and mark the future with its URL
						logger.debug(f"Display queue with: {kwargs['state']}")
						future_result[executor.submit(self.display.screenSwitcher, **kwargs)] = "Screen displayed: " + repr(kwargs["state"])
						# time.sleep(10)
						# self.screen_settled = True

					# Process any completed futures
					for future in done:
						result = future_result[future]
						try:
							data = future.result()
							if "Screen displayed" in result:
								self.screen_settled = True
							logger.debug(result)
						except Exception as exc:
							logger.exception('%r generated an exception: %s' % (result, exc))

						# Remove the now completed future
						del future_result[future]
					
				self.display.powerOff()
		except KeyboardInterrupt:
			pass

if __name__ == "__main__":
	Luminometer = Luminometer()

	try:
		Luminometer.run()

	except Exception as exc:
		logger.exception(f'Luminometer encountered exception: {exc}')
	finally:
		GPIO.cleanup()
		del(Luminometer)
		
		# Power down system
		# os.system('sudo poweroff')


