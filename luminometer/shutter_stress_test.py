#! /usr/bin/env python3
""" Class definition for a luminometer

-- Important Links --

ADC Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

Sensor Datasheet
	https://www.mouser.com/datasheet/2/308/MICROC-SERIES-D-1811553.pdf

"""
import time, math, csv, argparse, logging, enum
import logging.handlers as handlers
from datetime import datetime
import numpy as np
import os, json

from numpy.testing import measure
import RPi.GPIO as GPIO
import pigpio
import concurrent.futures
import threading
import queue
from typing import List
from statistics import mean, stdev

from adc_constants import *
from luminometer_constants import *
from ads131m08_reader import ADS131M08Reader, bytes_to_readable, CRCError
from menu import Menu, MenuStates

# Set up measurement, logging directories, and logger
if not os.path.exists(LOG_OUTPUT_DIR):
	os.mkdir(LOG_OUTPUT_DIR)
if not os.path.exists(MEASUREMENT_OUTPUT_DIR):
	os.mkdir(MEASUREMENT_OUTPUT_DIR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_location = os.path.join(LOG_OUTPUT_DIR, "luminometer.log")

# Set up logging to a file
file_handler = handlers.RotatingFileHandler(log_location, maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s: %(message)s", "%Y-%m-%d-%H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Set up logging to the console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Investigate _cb_adc time
now = datetime.now()
file_name = now.strftime("%Y-%b-%d-%H:%M:%S") + "-cb_timing.csv"
cb_log_location = os.path.join(LOG_OUTPUT_DIR, file_name)

# Investigate shutter timing
file_name = now.strftime("%Y-%b-%d-%H:%M:%S") + "-shutter_timing.csv"
shutter_open_location = os.path.join(LOG_OUTPUT_DIR, now.strftime("%Y-%b-%d-%H:%M:%S") + "-shutter_open.csv")
shutter_close_location = os.path.join(LOG_OUTPUT_DIR, now.strftime("%Y-%b-%d-%H:%M:%S") + "-shutter_close.csv")

STRESS_TEST = os.path.join(LOG_OUTPUT_DIR, "STRESS-TEST-" + now.strftime("%Y-%b-%d-%H:%M:%S") + ".csv")

if not os.path.exists(STRESS_TEST):
	append_write = "w"
else:
	append_write = "a"

# Write every fourth sample to save data 
f = open(STRESS_TEST, append_write, newline='')
raw = csv.writer(f)

#logger.disabled = True
class MeasurementType(enum.Enum):
	MEASUREMENT = enum.auto()
	TEMPERATURE_COMP = enum.auto()
	SENSITIVITY_NORM = enum.auto()

class HBridgeFault(Exception):
	pass

def better_sleep(sleep_time: float):
	"""
	A utility function for a more accurate sleep than using time.sleep().
	time.time() typically has microsecond accuracy, as compared to time.sleep() which
	has millisecond accuracy. However both functions are highly dependent on the operating
	system, CPU clock rate, and other platform-dependent factors. Note that like
	time.sleep(), this is a blocking delay.

	Arguments:
		- sleep_time: float
			How long to delay
	"""
	start = time.time()
	while time.time() - start < sleep_time:
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
		logger.info("Successfully instantiated LumiBuzzer.")

	def buzz(self):
		GPIO.output(self._buzzPin, 1)
		better_sleep(BUZZ_S)
		GPIO.output(self._buzzPin, 0)

class LumiShutter():
	# Uses RPi BCM pinout
	# Written to operate a TI DRV8833 H-bridge chip.
	# Each instance of this class drives just one channel; create a second instance to drive two channels.

	def __init__(self, dirPin: int, pwmPin: int, faultPin: int, sleepPin: int):
		try:
			self._pi = pigpio.pi()
			self._dirPin = int(dirPin)
			self._pwmPin = int(pwmPin)
			self._faultPin = int(faultPin)
			self._sleepPin = int(sleepPin)
			self.start_time = 0
			self.open_times = []
			self.close_times = []
			self.moving = False
		except TypeError:
			logger.error("Pin value not convertible to integer!")
			raise

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._dirPin, GPIO.OUT, initial = 0)
		self._pi.hardware_PWM(self._pwmPin, 0, 0)
		self.hbridge_err = "OK"

		GPIO.setup(self._sleepPin, GPIO.OUT, initial = 1)
		GPIO.setup(self._faultPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.output(self._sleepPin, 1)
		better_sleep(.2)

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
			print("Action must be a string!")
			return

		if not self._lock.locked():
			with self._lock:
				try:
					if action == 'open':
						self.driveOpen()
						better_sleep(driveTime)
						self.holdOpen()
						self.moving = False

					elif action == 'close':
						self.driveClosed()
						better_sleep(driveTime)
						self.holdClosed()
						self.moving = False

					else:
						print(f"Shutter command not recognized!")
				except Exception as e:
					logger.exception(f"Shutter actuation error: {e}")
					self.rest()

		return

	def saveShutterTimes(self):
		np.savetxt(shutter_open_location, self.open_times, delimiter=',')
		np.savetxt(shutter_close_location, self.close_times, delimiter=',')

	def rest(self):
		try:
			GPIO.output(self._dirPin, 0)
			self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, 0)
			logger.info("Turning off PWM, resting.")

		except:
			pass

	def driveOpen(self):
		logger.info(f"Opening shutter")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, 0)
		GPIO.output(self._dirPin, 1)
	
	def driveClosed(self):
		logger.debug(f"Closing shutter")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, SHUTTER_DRIVE_DR)
		GPIO.output(self._dirPin, 0)
	
	def holdOpen(self):
		logger.debug("Holding open.")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, 1000000 - SHUTTER_HOLD_DR)
		GPIO.output(self._dirPin, 1)

	def holdClosed(self):
		logger.debug("Holding closed.")
		self._pi.hardware_PWM(self._pwmPin, SHT_PWM_FREQ, SHUTTER_HOLD_DR)
		GPIO.output(self._dirPin, 0)

	def _faultDetected(self, channel):
		# Callback for handling an H-bridge fault pin event
		# Ref datasheet:
		# https://www.ti.com/lit/ds/symlink/drv8833.pdf?ts=1617084507643&ref_url=https%253A%252F%252Fwww.google.com%252F
		self.hbridge_err = "ERR"
		logger.exception("H-bridge fault detected!")
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

	def __init__(self, screen_type):

		self._setupGPIO()
		self.state = MenuStates.MAIN_MENU
		self.measurementMode = ""
		self.target_time = 0
		self.selected_calibration = ""
		self._duration_s = 0
		self.resultA = 0
		self.semA = float('inf')
		self.resultB = 0
		self.semB = float('inf')
		self.cb_buffer_size = 100
		self._crcErrs = 0
		self._accumBufferA = []
		self._accumBufferB = []
		self._accumSiPMRef = []
		self._accumSiPMBias = []
		self._accum34V = []
		self.cb_times = []
		self.button_held_duration = 0
		self._state_lock = threading.Lock()
		
		# Boolean internal variables
		self._powerOn = True
		self._measuring = False
		self._measurementIsDone = False
		self.screen_settled = True
		self._accumulate = True

		# Diagnostic menu info
		self.diag_vals = {
			"batt": "OK",
			"34V": "OK",
			"pbias": "OK",
			"num_CRC_errs": 0,
			"hbridge_err": "OK",
		}

		# Read RLU conversions and temperature calibrations
		self._readCalibrationFiles()

		# TODO, Get battery status dynamically
		self.batt_status = "OK"
		self.calA = " - NONE"
		logger.info("Checking to see if custom calibration file exists.")
		if os.path.isfile(CUSTOM_CAL_PATH):
			logger.info("Custom calibration file exists.")
			self.calA = ""

		logger.info("Instantiating display, shutter, and buzzer.")
		self.screen_type = screen_type
		self.display = Menu(screen_type, self.selected_calibration, self.batt_status)
		
		try:
			self.shutter = LumiShutter(SHT_1, SHT_PWM, SHT_FAULT, NSLEEP)
		except Exception as e:
			logger.exception("Error instantiating LumiShutter!")
		try:
			self.buzzer = LumiBuzzer(BUZZ)
		except Exception as e:
			logger.exception("Error instantiating LumiBuzzer!")

		# Start up the ADC
		self._initADC()

		# Get initial values from ADC
		self.adc_vals = [0]*5
		
		# Create thread-safe queues for hardware jobs
		logger.info("Creating display, shutter, and measure queues.")
		self._display_q = queue.Queue(maxsize=1)
		self._shutter_q = queue.Queue(maxsize=1)
		self._measure_q = queue.Queue(maxsize=1)
		self._measureLock = threading.Lock()

		self._resetBuffers()
		self.set_state(MenuStates.MAIN_MENU)
		
		logger.info("Successfully instantiated Luminometer.")
		logger.info("Starting shutter stress test.")
		exposure = 0.5e6 # seconds, approx 140 hrs
		self._measure_q.put_nowait((exposure, MeasurementType.MEASUREMENT))

	def _initADC(self):
		# Start up sensor chip
		try:
			logger.info("Starting up sensor chip.")
			self._adc_pi = pigpio.pi()
			self._adc = ADS131M08Reader()
			self._adc.setup_adc(SPI_CE, channels=[0,1,2,3,4])
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
			self._adc_pi.callback(self._adc._DRDY, pigpio.FALLING_EDGE, func=self._cb_adc_data_ready)

	def _setupGPIO(self):
		# Pin assignments
		self._btn1 = BTN_1
		self._btn2 = BTN_2
		self._btn3 = BTN_3
		self._FAN = FAN
		self._ADC_PWR_EN = ADC_PWR_EN
		self._PMIC_LBO = PMIC_LBO

		# Set up channels for button pushes
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self._btn1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._btn3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Set up low battery input
		GPIO.setup(self._PMIC_LBO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Set up sensor board power enable, and fan enable
		GPIO.setup(self._ADC_PWR_EN, GPIO.OUT, initial=1)
		GPIO.setup(self._FAN, GPIO.OUT, initial=1)

		# Add callback for button pushes	
		logger.info("Setting up button callbacks.")
		GPIO.add_event_detect(self._btn1, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn2, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)
		GPIO.add_event_detect(self._btn3, GPIO.FALLING, callback=self.unified_callback, bouncetime=200)

	def _readCalibrationFiles(self):

		# Get last selected calibration
		try:
			with open(LAST_CAL) as json_file:
				data = json.load(json_file)
				self.selected_calibration = data
				logger.info(f"Previously used calibration file found. Using {self.selected_calibration}.")
		except:
			logger.warning("Could not open last_chosen_cal.json, defaulting to standard calibration.")
			self.selected_calibration = DEFAULT_CAL_NAME

		self._tempCoeffs = {}

		try:
			if self.selected_calibration == CUSTOM_CAL_NAME:
				PATH = CUSTOM_CAL_PATH
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

		try:
			# Get RLU_PER_V
			with open(RLU_CAL_PATH) as json_file:
				data = json.load(json_file)
				self.rlu_per_v_a, self.rlu_per_v_b = data["RLU_PER_V_A"], data["RLU_PER_V_B"]
				logger.info("Sucessfully loaded RLU_PER_V from rlu.json.")
		except:
			# In case of an error, fallback on this default for rlu_per_v
			self.rlu_per_v_a = 50000
			self.rlu_per_v_b = 50000
			logger.exception(f"Errored while reading rlu_per_v from rlu.json.\nResorting to: ({self.rlu_per_v_a:}, {self.rlu_per_v_b:})")

	def checkAndSetBatteryStatus(self):
		# Check for a low battery
		if not GPIO.input(self._PMIC_LBO):
			self.batt_status = BATT_LOW
		else:
			self.batt_status = BATT_OK

	def _updateDiagVals(self):
		logger.info("Updating diagnostic values.")
		try:
			self.adc_vals = self.averageNMeasurements()
			self.diag_vals["batt"] = self.batt_status
			self.diag_vals["34V"] = self.adc_vals[4]
			self.diag_vals["pbias"] = self.adc_vals[3]
			self.diag_vals["num_CRC_errs"] = self._crcErrs
			self.diag_vals["hbridge_err"] = self.shutter.hbridge_err
		except:
			logger.exception("Error updating diagnostic values.")

	def _updateDisplayKwargs(self, next_state):
		display_kwargs = {
					"state": next_state,
					"battery_status": self.batt_status,
					"selected_calibration": self.selected_calibration,
					"calA": self.calA,
					"measurementMode": self.measurementMode,
					"time_elapsed": self._rsc,
					"target_time": self.nRawSamples,
					"_measurementIsDone": self._measurementIsDone,
					"resultA": self.resultA,
					"semA": self.semA,
					"resultB": self.resultB,
					"semB": self.semB,
					"diag_vals": self.diag_vals,
					"adc_vals": self.adc_vals,
					"rlu_per_v": [self.rlu_per_v_a, self.rlu_per_v_b],
					"rlu_time": SENSITIVITY_NORM_TIME
				}
		return display_kwargs

	def set_state(self, next_state: MenuStates):
		if not self._state_lock.locked():
			with self._state_lock:
				self.checkAndSetBatteryStatus()
				display_kwargs = self._updateDisplayKwargs(next_state)

				try:
					if self.screen_settled:
						if next_state == MenuStates.MAIN_MENU or next_state == MenuStates.STATUS_MENU:
							self._updateDiagVals()

						if not (next_state == MenuStates.MEASUREMENT_IN_PROGRESS):
							# Only buzz on taps, not holds (to avoid confusion on how long it was being held for)
							if self.button_held_duration == 0:
								self.buzzer.buzz()
								self.button_held_duration = 0
						logger.info(f"Transitioning: {self.state} --> {next_state}")
					
						self._display_q.put(display_kwargs)
						self.screen_settled = False
						self.state = next_state
				except queue.Full:
					logger.info("Display queue full.")
					pass
	
	def secretMenu(self, channel):
		if self.state == MenuStates.STATUS_MENU:
			nextState = None
			self.button_combo.append(channel)
			if self.button_combo == RLU_CALIBRATION_COMBO:
				nextState = MenuStates.RLU_CALIBRATION

			if nextState != None:
				self.set_state(nextState)

	def unified_callback(self, channel):
		# If the device is currently measuring
		# we only want the user to be able to trigger this callback if they are
		# pressing button 1 to trigger an abort
		if self._measuring and (channel == BTN_1 or channel == BTN_2):
			return
		
		button_pos = BTN_PIN_TO_POS[channel]
		self.secretMenu(channel)

		# Get duration of button hold
		buzz1s = buzz2s = buzz3s = buzz4s = buzz5s = True
		self.button_held_duration = 0
		startTime = time.perf_counter()
		while not GPIO.input(channel):
			self.button_held_duration = int(time.perf_counter() - startTime)
			if (self.button_held_duration == 1) and buzz1s:
				self.buzzer.buzz()
				buzz1s = False
				logger.info(f"{button_pos} button held for 1 second.")
			elif (self.button_held_duration == 2) and buzz2s:
				self.buzzer.buzz()
				buzz2s = False
				logger.info(f"{button_pos} button held for 2 seconds.")
			elif (self.button_held_duration == 3) and buzz3s:
				self.buzzer.buzz()
				buzz3s = False
				logger.info(f"{button_pos} button held for 3 seconds.")			
			elif (self.button_held_duration == 4) and buzz4s:
				self.buzzer.buzz()
				buzz4s = False
				logger.info(f"{button_pos} button held for 4 seconds.")
			elif (self.button_held_duration == 5) and buzz5s:
				self.buzzer.buzz()
				buzz5s = False
				logger.info(f"{button_pos} button held for 5 seconds.")

		if channel == BTN_1:
			self.btn1_transition_logic(self.button_held_duration)
		elif channel == BTN_2:
			self.btn2_transition_logic(self.button_held_duration)
		elif channel == BTN_3:
			self.btn3_transition_logic(self.button_held_duration)

	def btn1_transition_logic(self, duration):
		'''This is the bottom button
		'''
	
		logger.info(f"Button 1 (bottom) pressed.")
		nextState = None

		# Power off if bottom button held for 3s
		if duration == POWER_OFF_DURATION:
			nextState = MenuStates.CONFIRM_POWER_OFF
			logger.info('Moving to power off confirmation screen.')
			while not self.screen_settled:
				pass
			self._haltMeasurement = True

		elif self.state == MenuStates.MAIN_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.CALIBRATION_MENU

		elif self.state == MenuStates.MEASUREMENT_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.SHOW_FINAL_MEASUREMENT and duration == TRANSITION_DURATION:
			nextState = MenuStates.MEASUREMENT_MENU

		elif self.state == MenuStates.STATUS_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CALIBRATION_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CONFIRM_CALIBRATION and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.RLU_CALIBRATION and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU
		
		elif self.state == MenuStates.CONFIRM_POWER_OFF and duration == TRANSITION_DURATION:
			nextState = MenuStates.MAIN_MENU

		if nextState != None:
			self.set_state(nextState)

	def btn2_transition_logic(self, duration):
		'''This is the middle button
		'''

		logger.info(f"Button 2 (middle) pressed.")
		nextState = None

		if self.state == MenuStates.MAIN_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.STATUS_MENU
			# Set up special button combo memory
			self.button_combo = []

		elif self.state == MenuStates.MEASUREMENT_MENU:
			# Perform timed measurement
			if self.screen_settled:
				if not self._measuring:
					exposure = DURATION_TO_EXPOSURE[duration]
					self.target_time = exposure
			
					try:
						if not self._measureLock.locked():
							self._measure_q.put_nowait((exposure, MeasurementType.MEASUREMENT))
					except queue.Full:
						logger.info('Already busy measuring')

					self._duration_s = 0
					self.measurementMode = "TIMED"
					if duration == 0:
						self.buzzer.buzz()

		elif self.state == MenuStates.CALIBRATION_MENU:
			# Switch to custom calibration and return to main
			# or begin new calibration if held for 5 seconds
			
			calibrate = False

			if duration == HOLD_TO_CALIBRATE_TIME:
				calibrate = True
			
			# If held for 5s, prompt user to confirm they want to calibrate, otherwise load default
			if calibrate:
				logger.info("Button 2 held for 5 seconds, move to confirm calibration with user.")
				nextState = MenuStates.CONFIRM_CALIBRATION
			else:
				# Get constants
				logger.info("Attempt to load existing custom calibration.")
				try:
					if os.path.isfile(CUSTOM_CAL_PATH):
						logger.info("Found custom calibration file.")
						with open(CUSTOM_CAL_PATH,'r') as json_file:
							data = json.load(json_file)
							self._tempCoeffs = data
						
						# Set custom as last chosen calibration
						self.selected_calibration = CUSTOM_CAL_NAME
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
		'''This is the top button
		'''

		logger.info(f"Button 3 (top) pressed.")
		nextState = None

		if self.state == MenuStates.MAIN_MENU and duration == TRANSITION_DURATION:
			nextState = MenuStates.MEASUREMENT_MENU

		elif self.state == MenuStates.MEASUREMENT_MENU and duration == TRANSITION_DURATION:
			if self.screen_settled:
				if not self._measuring:
					self.measurementMode = "AUTO"
					self._duration_s = 0
					self.target_time = None

					exposure = 0
					try:
						if not self._measureLock.locked():
							self._measure_q.put_nowait((exposure, MeasurementType.MEASUREMENT))
					except queue.Full:
						logger.info('Already busy measuring')
					self.buzzer.buzz()
		elif self.state == MenuStates.MEASUREMENT_IN_PROGRESS and duration == ABORT_MEASUREMENT_DURATION:
			# Abort and return to measurement menu if top button held for the abort duration
			logger.info(f"Button 3 held for {ABORT_MEASUREMENT_DURATION} seconds - halting measurement.")
			self.buzzer.buzz()
			self._haltMeasurement = True
			nextState = MenuStates.MEASUREMENT_MENU
			while not self.screen_settled:
				pass
		
		elif self.state == MenuStates.CALIBRATION_MENU and duration == TRANSITION_DURATION:
			# Switch to standard calibration and return to main
			self.selected_calibration = DEFAULT_CAL_NAME
			self.display.set_selected_calibration(self.selected_calibration)

			# Get constants
			with open(STANDARD_CAL_PATH,'r') as json_file:
				data = json.load(json_file)
				self._tempCoeffs = data
			
			# Set default as last chosen calibration
			with open(LAST_CAL, "w") as json_file:
				json.dump(self.selected_calibration, json_file)
				
			nextState = MenuStates.MAIN_MENU

		elif self.state == MenuStates.CONFIRM_CALIBRATION and duration == TRANSITION_DURATION:
			# Perform calibration
			if not self._measureLock.locked():
				try:
					logger.info("Performing calibration.")
					self._measure_q.put_nowait((DEF_DARK_TIME, MeasurementType.TEMPERATURE_COMP))
				except queue.Full:
					pass
		elif self.state == MenuStates.RLU_CALIBRATION and duration == TRANSITION_DURATION:
			# Start RLU calibration
			if not self._measureLock.locked():
				try:
					logger.info("Performing RLU calibration.")
					self.target_time = SENSITIVITY_NORM_TIME
					self._measure_q.put_nowait((SENSITIVITY_NORM_TIME, MeasurementType.SENSITIVITY_NORM))
				except queue.Full:
					pass
				self.buzzer.buzz()

		elif self.state == MenuStates.CONFIRM_POWER_OFF and duration == TRANSITION_DURATION:
			if self.screen_settled:
				self.buzzer.buzz()
				self.powerOffSequence()
					
		if nextState != None:
			self.set_state(nextState)

	def powerOffSequence(self):
		while self._display_q.full() or not self.screen_settled:
			pass
		self._display_q.put_nowait({"state": MenuStates.POWER_OFF})
		better_sleep(0.5)
		while not self.screen_settled:
			pass
		# self.shutter.saveShutterTimes()
		# self.saveADCTimes()
		self._powerOn = False
		logger.info("POWER OFF.")

	def convertToRLU(self, data, sensor: str):
		'''Converts the raw data and standard error of mean with the RLU scaling and offset'''

		if sensor == "A":
			rlu_per_v = self.rlu_per_v_a
		elif sensor == "B":
			rlu_per_v = self.rlu_per_v_b

		data_RLU = ( rlu_per_v * mean(data) ) + ADD_OFFSET_RLU

		# Can't compute stdev unless there are >3 shutter-open periods _|-|_|-|_|-|_
		if self._sc > 5:
			sem_RLU = rlu_per_v * ( stdev(data)/math.sqrt(float(len(data))) ) 
		else:
			sem_RLU = float('inf')

		return data_RLU, sem_RLU

	def updateAndSaveRLU(self):
		'''Updates the RLU_PER_V for both sensors and saves it to rlu.json'''
		logger.info("Updating RLU_PER_V_A and RLU_PER_V_B values.")
		try:
			self.rlu_per_v_a = (TARGET_RLU - ADD_OFFSET_RLU) / mean(self.dataA)
			self.rlu_per_v_b = (TARGET_RLU - ADD_OFFSET_RLU) / mean(self.dataB)
			updated_rlu = {
				"RLU_PER_V_A": self.rlu_per_v_a,
				"RLU_PER_V_B": self.rlu_per_v_b
			}

			# Save to rlu.json
			with open(RLU_CAL_PATH,'w') as outfile:
					json.dump(updated_rlu, outfile)
		except:
			logger.exception("Errored while updating/saving RLU A/B values.")
	
	def measure(self, \
		measure_time: int = 30, \
		measurement_type: MeasurementType = MeasurementType.MEASUREMENT):
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
							self.dataA, _ = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, "A", MeasurementType.MEASUREMENT)
							self.dataB, _ = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, "B", MeasurementType.MEASUREMENT)
							
							# Recalculate mean
							self.resultA, self.semA = self.convertToRLU(self.dataA, "A")
							self.resultB, self.semB = self.convertToRLU(self.dataB, "B")

							logger.debug(f"Sensor A after {int(self._sc/2)} cycles: {self.resultA:.2f}")
							logger.debug(f"Sensor A raw: {self.rawdataA[self._rsc-1]:.8f}")
							logger.debug(f"Sensor B after {int(self._sc/2)} cycles: {self.resultB:.2f}")
							logger.debug(f"Sensor B raw: {self.rawdataB[self._rsc-1]:.8f}")

							self._duration_s = time.perf_counter() - t0

							self._updateDisplayResult()

							sampleCount += 1

					# Final: gate traces. If calibration, do the fit and write the file
					self.dataA, self._darkDownsampledA = self.gateTrace(self.rawdataA[:self._rsc], self.shutter_samples, "A", measurement_type)
					self.dataB, self._darkDownsampledB = self.gateTrace(self.rawdataB[:self._rsc], self.shutter_samples, "B", measurement_type)	

					# Final result is the mean of all the gated shutter-open periods
					self.resultA, self.semA = self.convertToRLU(self.dataA, "A")
					self.resultB, self.semB = self.convertToRLU(self.dataB, "B")

					# If doing a calibration, then store the result
					if measurement_type == MeasurementType.TEMPERATURE_COMP:
						try:
							logger.info("Creating calibration fit parameters.")
							fitParamsA = np.polyfit(self._darkDownsampledA, self.dataA, 1, full=False)
							fitParamsB = np.polyfit(self._darkDownsampledB, self.dataB, 1, full=False)
							
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

							# Save calibration temperature coefficients
							with open(CUSTOM_CAL_PATH,'w') as outfile:
								logger.info("Saving custom temperature calibration coefficients.")
								json.dump(self._tempCoeffs, outfile)

							# Set the custom calibration to be the one used on next boot
							self.selected_calibration = CUSTOM_CAL_NAME
							with open(LAST_CAL, "w") as json_file:
								logger.info("Setting last calibration as custom.")
								json.dump(self.selected_calibration, json_file)
							self.display.set_selected_calibration(self.selected_calibration)
						except:
							logger.exception("Error generating/saving calibration fit parameters.")

					# If doing a sensitivity normalization, calculate normalization and save to rlu.json
					elif measurement_type == MeasurementType.SENSITIVITY_NORM:
						self.updateAndSaveRLU()

					logger.info(f"Sensor A final result: {self.resultA:.2f} +/- {self.semA:.2f} (s.e.m.) ")
					logger.info(f"Sensor B final result: {self.resultB:.2f} +/- {self.semB:.2f} (s.e.m.) ")
					logger.info(f"{self._rsc} samples in {time.perf_counter() - t0} seconds. Sample rate of {self._rsc / (time.perf_counter() - t0)} Hz")
					logger.info(f"{self._crcErrs} CRC Errors encountered.")

					self.writeToFile()
				
				except KeyboardInterrupt as exc:
					#self.writeToFile('Interrupted_')
					logger.error("Keyboard interrupted measurement")
				finally:
					self._measuring = False
					self._measurementIsDone = True
					if measurement_type == MeasurementType.SENSITIVITY_NORM:
						while not self.screen_settled:
							pass
						self.set_state(MenuStates.RLU_CALIBRATION)
					elif not self._haltMeasurement:
						self._updateDisplayResult(show_final=True)
					self._duration_s = time.perf_counter() - t0
					self.shutter.rest()
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

	def averageNMeasurements(self) -> List[float]:
		'''
		Average N sequential measurements from the sensors without using the shutters.
		This method uses the _cb_adc_data_ready() callback that always runs while the
		ADC is on. We simply initialize new lists (one for each channel), set the 
		_accumulate flag to True, and wait for them to fill up.
		'''
		output = [0]*5

		try:
			output = [mean(self._accumBufferA), mean(self._accumBufferB), \
			mean(self._accumSiPMRef), mean(self._accumSiPMBias), \
			mean(self._accum34V)]
		except Exception as e:
			print(e)

		return output

	def _cb_adc_data_ready(self, channel, level, tick):
		# Callback function executed when data ready is asserted from ADC
		# The callback also queues the shutter actions, in order to stay synchronized 
		# with the data readout.
		if self._simulate:
			# Simulation mode
			d = [0.0, 0.0, 0.0, 0.0, 0.0]
			threading.Timer(SAMPLE_TIME_S, self._cb_adc_data_ready, args=(DRDY,)).start()
		else:
			try:
				if not self.shutter.moving:
					# Read sensor
					d = self._adc.read()
					self.adc_vals = d

			# ADC communication error
			except CRCError:
				# Only worry about CRC errors that occur during a measurement (**Check with Paul)
				# Note to self: this is a temporary band-aid fix as I try to figure out why the CRC errors
				# are randomly occurring on first boot
				if self._measuring:
					self._crcErrs += 1
				return
	
		if self._measuring and (self._rsc < self.nRawSamples) and not self._haltMeasurement and not self.shutter.moving:
			self.rawdataA[self._rsc] = d[0]
			self.rawdataB[self._rsc] = d[1]

			if not os.path.exists(STRESS_TEST):
				append_write = "w"
			else:
				append_write = "a"

			# Write every fourth sample to save data 
			if self._rsc % 4 == 0:
				raw.writerow((self.rawdataA[self._rsc], self.rawdataB[self._rsc]))

			# Close shutters
			if self._rsc % (2*self.shutter_samples) == 0:
				try:
					self.shutter.moving = True
					self._shutter_q.put_nowait('close')
				except queue.Full:
					pass

			# Open shutters
			elif self._rsc % self.shutter_samples == 0:
				try:
					self.shutter.moving = True
					self._shutter_q.put_nowait('open')
				except queue.Full:
					pass

			self._rsc += 1
			self._sc = int(self._rsc/self.shutter_samples)

		if self._accumulate:
			if len(self._accumBufferA) > self.cb_buffer_size:
				self._accumBufferA.pop(0)
				self._accumBufferB.pop(0)
				self._accumSiPMRef.pop(0)
				self._accumSiPMBias.pop(0)
				self._accum34V.pop(0)

			self._accumBufferA.append(d[0])
			self._accumBufferB.append(d[1])
			self._accumSiPMRef.append(d[2])
			self._accumSiPMBias.append(d[3])
			self._accum34V.append(d[4])
		
		return		

	def saveADCTimes(self):
		np.savetxt(cb_log_location, self.cb_times, delimiter=',')

	def _updateDisplayResult(self, show_final: bool = False):
		# Update display with intermediate results
		logger.debug("Updating intermediate results.")
		self.resultA, self.semA = self.convertToRLU(self.dataA, "A")
		self.resultB, self.semB = self.convertToRLU(self.dataB, "B")
	
		try:
			if show_final:
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
			logger.error('Display queue full. Could not display result')

	def _resetBuffers(self, measure_time: int = 10):

			self.dataA = [0.0]
			self.dataB = [0.0]
			self._darkDownsampledA = [0.0]
			self._darkDownsampledB = [0.0]
			self.semA = float('inf')
			self.semB = float('inf')
			self.resultA = 0.0
			self.resultB = 0.0
			self._measurementIsDone = False
			self._haltMeasurement = False
			self._accumBufferA = []
			self._accumBufferB = []
			self._accumSiPMRef = []
			self._accumSiPMBias = []
			self._accum34V = []
			self._accumulate = False

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

			# Raw samples are continuous and include open and closed periods
			self.nRawSamples = self.shutter_samples*(self.nSamples + self.nDark)

			self.rawdataA = self.nRawSamples*[None]
			self.rawdataB = self.nRawSamples*[None]
			self._duration_s = 0.0

			# Counters
			self._rsc = self._sc = self._crcErrs = 0

	def writeToFile(self):
		now = datetime.now()
		dt_string = now.strftime("%Y-%m-%d-%H-%M-%S")

		### Write the final result to the all-measurements.csv file
		file = os.path.join(MEASUREMENT_OUTPUT_DIR, ALL_MEASUREMENTS_CSV_FILENAME)
		try:
			# Create the all measurements file if it doesn't already exist
			if not os.path.exists(file):
				# Create file
				headers = [
					"date", 
					"measurementMode", 
					"exposure", 
					"resultA", 
					"standard_err_of_mean_A",
					"resultB",
					"standard_err_of_mean_B",
				]
				# Add header row
				with open(file, 'w+', newline='') as final_measurements_csv:
					csvWriter = csv.writer(final_measurements_csv)
					csvWriter.writerow(headers)
					final_measurements_csv.close()
		except:
			logger.exception("Errored while creating all-measurements.csv.")
		try:
			# Append final measurement to all-measurements.csv
			measurements = [
				dt_string,
				self.measurementMode,
				self.target_time,
				self.resultA,
				self.semA,
				self.resultB,
				self.semB
			]
			with open(file, 'a', newline='') as final_measurements_csv:
				csvWriter = csv.writer(final_measurements_csv)
				csvWriter.writerow(measurements)
				final_measurements_csv.close()
		except:
			logger.exception("Errored while appending to all-measurements.csv.")
		
		### Write all intermediate raw and gated data results to a DATE.csv and DATE_gated.csv
		title = os.path.join(MEASUREMENT_OUTPUT_DIR, dt_string)
		try:
			logger.info(f"Saving to {title}")
			with open(title + '.csv', 'w', newline='') as csvFile:
				csvWriter = csv.writer(csvFile)
				for i in range(self.nRawSamples):
					csvWriter.writerow((self.rawdataA[i], self.rawdataB[i]))

			with open(title + '_gated' + '.csv', 'w', newline='') as csvFile:
				csvWriter = csv.writer(csvFile)
				for i in range(len(self.dataA)):
					csvWriter.writerow((self.dataA[i], self.dataB[i]))

			with open(title + '_darkDownsampled' + '.csv', 'w', newline='') as csvFile:
				csvWriter = csv.writer(csvFile)
				for i in range(len(self.dataA)):
					csvWriter.writerow((self._darkDownsampledA[i], self._darkDownsampledB[i]))
			logger.info("File successfully saved.")
		except:
			logger.exception("Could not save measurement to file.")

	def gateTrace(self, \
		rawData: List[float], \
		gateSize: int, \
		channel: str, \
		measurement_type: MeasurementType = MeasurementType.MEASUREMENT) -> List[float]:
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
		darkDownsampled = []

		for i in range(gateSize, gateSize*nPeriods, 2*gateSize):
			sample = mean(rawData[(i+SKIP_SAMPLES):i+(gateSize-1)])
			darkBefore = mean(rawData[(i-gateSize+SKIP_SAMPLES):(i-1)])
			darkAfter = mean(rawData[(i+gateSize+SKIP_SAMPLES):(i+2*gateSize - 1)])
			darkMean = 0.5*(darkBefore + darkAfter)

			darkDownsampled.append(darkMean)
			gatedSample = sample - darkMean

			if measurement_type == MeasurementType.TEMPERATURE_COMP:
				samples.append(gatedSample)
			else:
				samples.append(self.correctTemperature(gatedSample, darkMean, self._tempCoeffs[channel]))

		return samples, darkDownsampled

	def correctTemperature(self, gatedIn: float, darkMeanIn: float, tempCoeffs: List[float]) -> float:
		return gatedIn - tempCoeffs[1]*(darkMeanIn - tempCoeffs[0])

	def run(self):

		self.shutter.rest()

		try:
			with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:

				# Start a future for thread to submit work through the queue
				future_result = { \
					executor.submit(Luminometer.shutter.rest): 'SHUTTER RESTING', \
					}

				logger.info('Ready and waiting for button pushes...')

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

		except KeyboardInterrupt:
			pass

if __name__ == "__main__":
	screen_type = 2
	try:
		with open(SCREEN_TYPE_PATH) as json_file:
			data = json.load(json_file)
			screen_type = data["SCREEN_TYPE"]
			logger.info("Sucessfully loaded screen_type from screen_type.json.")
	except:
		logger.exception("Error reading screen_type from screen_type.json. Defaulting to screen_type=2.")

	Luminometer = Luminometer(screen_type)

	try:
		Luminometer.run()

	except Exception as exc:
		logger.exception(f'Luminometer encountered exception: {exc}')
	finally:
		GPIO.cleanup()
		del(Luminometer)
		f.close()
		
		# Power down system
		os.system('sudo poweroff')


