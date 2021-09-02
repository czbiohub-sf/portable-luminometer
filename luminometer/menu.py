#!/usr/bin/env python3
import logging
import logging.handlers as handlers
import enum
import os
import threading
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from font_intuitive import Intuitive
from inky.auto import auto
from inky import InkyPHAT, InkyPHAT_SSD1608
import numpy as np
from luminometer_constants import *

# Set up logging directory and logger
LOG_OUTPUT_DIR = "/home/pi/luminometer-logs/"
if not os.path.exists(LOG_OUTPUT_DIR):
	os.mkdir(LOG_OUTPUT_DIR)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_location = os.path.join(LOG_OUTPUT_DIR, "menu.log")

# Set up logging to a file
file_handler = logging.FileHandler(log_location)
file_handler = handlers.RotatingFileHandler(log_location, maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s: %(message)s", "%Y-%m-%d-%H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Set up logging to the console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

"""
An enum which lists the possible MenuStates. enum.auto() is used to 
automatically generate unique constants corresponding to each state.
If a new menu screen is to be added, a new state should be added to the enum
as well.
"""
class MenuStates(enum.Enum):
    MAIN_MENU = enum.auto()
    MEASUREMENT_MENU = enum.auto()
    MEASUREMENT_IN_PROGRESS = enum.auto()
    SHOW_FINAL_MEASUREMENT = enum.auto()
    STATUS_MENU = enum.auto()
    CALIBRATION_MENU = enum.auto()
    CONFIRM_CALIBRATION = enum.auto()
    CALIBRATION_IN_PROGRESS = enum.auto()
    CONFIRM_POWER_OFF = enum.auto()
    POWER_OFF = enum.auto()
    RLU_CALIBRATION = enum.auto()

class Menu():
    """
    """
    def __init__(self, screen_type, calibration, battery_status):
        
        logger.info("Creating an InkyPHAT...")
        if screen_type == 1:
            logger.info("Screen: InkyPHAT")
            self.inky_display = InkyPHAT("black")
            scale_size = 1.3
        else:
            logger.info("Screen: InkyPHAT_SSD1608")
            self.inky_display = InkyPHAT_SSD1608("black")
            scale_size = 1.5
        self.rotation_deg = 0
        
        self._status_bar_offset = 15
        self.selected_calibration = calibration
        self.battery_status = battery_status
        self.screen_type = screen_type
        self._lock = threading.Lock()

        # Load the fonts
        logger.info("Setting up fonts.")
        # scale_size = 1.3
        self.intuitive_font = ImageFont.truetype(Intuitive, int(20 * scale_size))
        self.hanken_bold_font = ImageFont.truetype(HankenGroteskBold, int(33 * scale_size))
        self.hanken_medium_font = ImageFont.truetype(HankenGroteskMedium, int(13 * scale_size))
        self.hanken_small_font = ImageFont.truetype(HankenGroteskMedium, int(8 * scale_size))

        logger.info("Successfully instantiated Menu.")

    def set_selected_calibration(self, calibration):
        """
        Changes the currently set calibration. statusBar() uses this
        parameter.
        """
        logger.info(f"Setting calibration: {calibration}.")
        self.selected_calibration = calibration

    def set_battery_status(self, battery_status):
        """
        Changes the currently set battery status. statusBar() uses this
        parameter.
        """
        logger.info(f"Changing battery status: {battery_status}")
        self.battery_status = battery_status

    def statusCheckAll(self, adc_vals, battery_status, crc_errs):
        """TODO
        Takes in a set of five adc values which correspond to: 
        - Sensor A
        - Sensor B
        - SiPM Ref
        - SiPM Bias
        - 34V
        and checks that those values fall within an expected range.
        This returns "OK" or "ERR", which is then displayed in the "Status" option
        on the main menu screen.
        """

        siPMRef = adc_vals[2]
        siPMBias = adc_vals[3]
        v_34 = adc_vals[4]
        errs = "ERR - "

        if battery_status == "LO":
            return "BATT LOW"
        if crc_errs > 0:
            errs += "C"
        if not (V_34_MIN <= v_34 <= V_34_MAX):
            errs += "V"
        if not (SIPMREF_MIN <= siPMRef <= SIPMREF_MAX):
            errs += "R"
        if not (SIPMBIAS_MIN <= siPMBias <= SIPMBIAS_MAX):
            errs += "B"

        return errs
    def screenSwitcher(self, **kwargs):

        if not self._lock.locked():
            with self._lock:
                state = kwargs["state"]

                try:
                    # Display screens 
                    if state == MenuStates.MAIN_MENU:
                        self.set_battery_status(kwargs["battery_status"])
                        self.set_selected_calibration(kwargs["selected_calibration"])
                        self.mainMenu(kwargs["adc_vals"], kwargs["battery_status"], kwargs["crcErrs"])
                        logger.info("Switched to MainMenu screen.")

                    elif state == MenuStates.MEASUREMENT_MENU:
                        self.measurementMenu()
                        logger.info("Switched to Measurement screen.")

                    elif state == MenuStates.MEASUREMENT_IN_PROGRESS:
                        self.measurementInProgress(kwargs["resultA"], kwargs["semA"], kwargs["resultB"], 
                                                    kwargs["semB"], kwargs["target_time"], kwargs["time_elapsed"])
                        logger.info("Switched to MeasurementInProgress screen.")

                    elif state == MenuStates.SHOW_FINAL_MEASUREMENT:
                        self.showMeasurement(kwargs["_measurementIsDone"], kwargs["resultA"], kwargs["semA"], 
                                                kwargs["resultB"], kwargs["semB"], kwargs["target_time"], kwargs["time_elapsed"])
                        logger.info("Switched to ShowFinalMeasurement screen.")

                    elif state == MenuStates.STATUS_MENU:
                        self.statusMenu(kwargs["diag_vals"], kwargs["adc_vals"])
                        logger.info("Switched to Status screen.")

                    elif state == MenuStates.CALIBRATION_MENU:
                        self.calibrationMenu(kwargs["calA"])
                        logger.info("Switched to Calibration screen.")

                    elif state == MenuStates.CONFIRM_CALIBRATION:
                        self.confirmCalibrationOverwrite()
                        logger.info("Switched to ConfirmCalibration screen.")

                    elif state == MenuStates.CALIBRATION_IN_PROGRESS:
                        self.calibrationInProgress()
                        logger.info("Switched to CalibrationInProgress screen.")
                    
                    elif state == MenuStates.POWER_OFF:
                        self.powerOff()
                        logger.info("Switched to PowerOff screen.")

                    elif state == MenuStates.CONFIRM_POWER_OFF:
                        self.confirmPowerOff()
                        logger.info("Switched to ConfirmPowerOff screen.")

                    elif state == MenuStates.RLU_CALIBRATION:
                        self.rluCalibration(kwargs["rlu_time"], kwargs["rlu_per_v"])
                        logger.info("Switched to rluCalibration screen.") 

                    if self.screen_type == 2:
                        sleep(SCREEN2_DELAY)
                        
                except Exception as e:
                    logger.exception("Error encountered while switching screens.")

    def statusBar(self, draw):
        status = f"Cal: {self.selected_calibration} / Batt: {self.battery_status}"
        statusx, _ = self.hanken_small_font.getsize(status)
        x_pos = self.inky_display.resolution[0] - statusx
        draw.text((x_pos, 0), status, self.inky_display.BLACK, font=self.hanken_small_font)

    def mainMenu(self, adc_vals, battery_status, crc_errs):

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        status = self.statusCheckAll(adc_vals, battery_status, crc_errs)
        self.statusBar(draw)

        option1 = "> Measurement"
        option2 = "> Status - " + status #TODO Change to update '- OK' dynamically
        option3 = "> Choose calibration"
        subtext = "   > Hold bottom button for 5s on any screen"
        subtext2 = "       to go to power off confirmation screen."
        option1y = 1.5*self.hanken_medium_font.getsize(option1)[1] + self._status_bar_offset
        option2y = 1.5*self.hanken_medium_font.getsize(option2)[1] + option1y
        option3y = self.hanken_medium_font.getsize(subtext)[1] + option2y
        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option1y), option2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option2y), option3, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option3y), subtext, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option3y+13), subtext2, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def measurementMenu(self):

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        option1 = "> Autoexposure"
        option1_sub = ""
        option2 = "> Timed exposure"
        option2_sub1 = "Tap: 5 samples"
        option2_sub2 = "Hold to increase: 15->30->50->300"
        option3 = "> Back to main"

        option1y = self.hanken_medium_font.getsize(option1)[1] + self._status_bar_offset
        option1suby = self.hanken_small_font.getsize(option1_sub)[1] + option1y
        option2y = self.hanken_medium_font.getsize(option2)[1] + option1suby
        option2sub1y = self.hanken_small_font.getsize(option2_sub1)[1] + option2y
        option2sub2y = self.hanken_small_font.getsize(option2_sub2)[1] + option2sub1y
        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option1y), option1_sub, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option1suby), option2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option2y), option2_sub1, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option2sub1y), option2_sub2, self.inky_display.BLACK, self.hanken_small_font)
        draw.text((0, option2sub2y), option3, self.inky_display.BLACK, self.hanken_medium_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def calibrationInProgress(self):
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        line = "Calibration in progress"

        line1x, line1y = self.hanken_medium_font.getsize(line)

        draw.text((width/2 - line1x/2, height/2 - line1y/2), line, self.inky_display.BLACK, font=self.hanken_medium_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def measurementInProgress(self, sensorA: float=0.0, sensorA_sem: float=0.0,
                            sensorB: float=0.0, sensorB_sem: float=0.0, target_s: int=0, 
                            time_elapsed: int=0):

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        if target_s == None:
            target_s = "N/A" # For auto-exposure
        else:
            target_s = str(int(target_s))

        line0 = "> Hold TOP button for 3s to abort"
        line1 = "Measurement in progress..."
        line2 = f"A: {sensorA:.2f}+/-{sensorA_sem:.2f}"
        line3 = f"B: {sensorB:.2f}+/-{sensorB_sem:.2f}"
        line4 = f"Samples: {int(time_elapsed):n}/{target_s}"
        
        lines = [line1, line2, line3, line4]
        
        top_offset = self._status_bar_offset + self.hanken_small_font.getsize(line0)[1] + 5
        draw.text((0, self._status_bar_offset), line0, self.inky_display.BLACK, font=self.hanken_small_font)
        y_offset = top_offset
        for i, line in enumerate(lines):
            if i != 0:
                y_offset = y_offset + self.hanken_small_font.getsize(line)[1] + 5
            if i == 3:
                font = self.hanken_small_font
            else:
                font = self.hanken_medium_font
            draw.text((0, y_offset), line, self.inky_display.BLACK, font=font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def confirmPowerOff(self):
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        # self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        line = "Do you want to power off?"
        line2 = "> YES - top button"
        line3 = "> NO - bottom button"

        line1x, line1y = self.hanken_medium_font.getsize(line)
        line2y = line1y + self.hanken_small_font.getsize(line2)[1] + 10
        line3y = line2y + self.hanken_small_font.getsize(line3)[1] + 35

        draw.text((width/2 - line1x/2, line1y), line, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, line2y), line2, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line3y), line3, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def powerOff(self):
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        # self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        line = "POWERED OFF"

        line1x, line1y = self.hanken_medium_font.getsize(line)

        draw.text((width/2 - line1x/2, height/2 - line1y/2), line, self.inky_display.BLACK, font=self.hanken_medium_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def showMeasurement(self, final: bool=False, sensorA: float=0.0, sensorA_sem: float=0.0,
                            sensorB: float=0.0, sensorB_sem: float=0.0, target_s: int=0, time_elapsed: int=0):


        if target_s == None:
            target_s = "N/A" # For auto-exposure
            measurement_type = "Auto"
        else:
            target_s = str(int(target_s))
            measurement_type = f"Timed ({target_s})"

        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        line1 = "Final:" + ('Yes' if final == True else 'No') 
        line2 = f"A: {sensorA:.2f}+/-{sensorA_sem:.2f}"
        line3 = f"B: {sensorB:.2f}+/-{sensorB_sem:.2f}"
        line4 = f"Samples: {int(time_elapsed):n}/{target_s}"

        line5 = f"> Redo measurement (middle) - {measurement_type}"
        line6 = "> Clear and go to measurement menu (bottom)"
        lines = [line1, line2, line3, line4]

        y_offset = 10
        for i, line in enumerate(lines):
            if i != 0:
                y_offset = y_offset + self.hanken_small_font.getsize(line)[1] + 5
            if i == 3:
                font = self.hanken_small_font
            else:
                font = self.hanken_medium_font

            draw.text((0, y_offset), line, self.inky_display.BLACK, font=font)

        line4y = y_offset + self.hanken_small_font.getsize(line4)[1] + 10
        line5y = line4y + self.hanken_small_font.getsize(line5)[1] + 10
        draw.text((0, line4y), line5, self.inky_display.BLACK, font=font)
        draw.text((0, line5y), line6, self.inky_display.BLACK, font=font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def statusMenu(self, diag_vals, adc_vals):

        # Convert adc-vals according to 
        # https://docs.google.com/spreadsheets/d/1XpI4IkymO6xYV3iuJ1ECH5WIgAFEHEqbSMnkVcQrlJA/edit#gid=1958620632

        adc_vals[2] = (adc_vals[2]+0.6)*2       # SiPM ref
        adc_vals[3] = (adc_vals[3]+0.6)*2*28    # SiPM bias check
        adc_vals[4] = (adc_vals[4]+0.6)*2*28    # 34 V supply

        if len(adc_vals) < 5:
            print("Error: Too few ADC values")
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        yn_spaces = 2*self.inky_display.resolution[0] // 6
        adc_spaces = 3*self.inky_display.resolution[0] // 5
        adc_val_spaces = 5*self.inky_display.resolution[0] // 6

        line1 = "Low Battery:"
        line2 = "34V in range:"
        line3 = "PBias in range:"
        line4 = "CRC Err:"
        line5 = "H-Bridge Err:"
        line6 = "> Return to main menu"
        lines = [line1, line2, line3, line4, line5]
        diag_val_keys = ["batt", "34V", "pbias", "num_CRC_errs", "hbridge_err"]
        adc_val_keys = ["SensorA", "SensorB", "SiPMRef", "SiPMBias", "34V"]

        # TODO change the constants to something we get from luminometer_constants (or some JSON file etc.)
        # Check if 34V and PBias are in range
        P_BIAS_LOW = 29
        P_BIAS_HIGH = 32
        pbias = adc_vals[3]
        if pbias < P_BIAS_LOW:
            diag_vals["pbias"] = "LO"
        elif pbias > P_BIAS_HIGH:
            diag_vals["pbias"] = "HI"
        else:
            diag_vals["pbias"] = "OK"

        v34_LOW = 30
        v34_HIGH = 36
        v34 = adc_vals[4]
        if v34 < v34_LOW:
            diag_vals["34V"] = "LO"
        elif v34 > v34_HIGH:
            diag_vals["34V"] = "HI"
        else:
            diag_vals["34V"] = "OK"

        space = " "
        space_x, _ = self.hanken_small_font.getsize(space)

        for i, (line, key) in enumerate(zip(lines, diag_val_keys)):
            linex, _ = self.hanken_small_font.getsize(line)
            if adc_vals[i] < 0:
                adc_spaces -= 1

            num_spaces = (yn_spaces-linex) // space_x
            line = line + " "*int(num_spaces) + str(diag_vals[key])
            linex, _ = self.hanken_small_font.getsize(line)
            num_spaces = (adc_spaces-linex) // space_x

            line = line + " "*int(num_spaces) + f"{adc_val_keys[i]}:"
            linex, _ = self.hanken_small_font.getsize(line)
            val_spaces = (adc_val_spaces-linex) // space_x
            line = line + " "*int(val_spaces) + f"{adc_vals[i]:.3f}"
            lines[i] = line
        
        line1y = self.hanken_small_font.getsize(lines[0])[1] + self._status_bar_offset
        line2y = self.hanken_small_font.getsize(lines[1])[1] + line1y
        line3y = self.hanken_small_font.getsize(lines[2])[1] + line2y
        line4y = self.hanken_small_font.getsize(lines[3])[1] + line3y
        line5y = self.hanken_small_font.getsize(lines[4])[1] + line4y

        draw.text((0, self._status_bar_offset), lines[0], self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line1y), lines[1], self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line2y), lines[2], self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line3y), lines[3], self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line4y), lines[4], self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, self.inky_display.resolution[1]-20), line6, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def calibrationMenu(self, calibration_name):

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        option1 = "> Restore default calibration"
        option2 = f"> Custom calibration{calibration_name}"
        option3 = "> Return to main menu"
        subtext = "- HOLD the middle button for 5s to"
        subtext2 = "  overwrite custom calibration"

        option_offset = 8
        
        option1y = self._status_bar_offset + self.hanken_medium_font.getsize(option1)[1] + option_offset
        option2y = option1y + self.hanken_medium_font.getsize(option2)[1] + option_offset
        option3y = option2y + self.hanken_medium_font.getsize(option3)[1] + 7
        sub1y = option3y + self.hanken_small_font.getsize(subtext)[1]

        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option1y), option2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option2y), option3, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option3y), subtext, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, sub1y), subtext2, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def confirmCalibrationOverwrite(self):

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)
        
        line0 = "CAUTION"
        line1 = "This will overwrite any existing custom"
        line2 = " calibration. Are you sure?"
        line3 = "> YES - top button"
        line4 = "> ----------"
        line5 = "> NO - bottom button"
        
        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]
        line0y = self.hanken_medium_font.getsize(line0)[1] + self._status_bar_offset
        line1y = self.hanken_small_font.getsize(line1)[1] + line0y
        line2y = self.hanken_small_font.getsize(line2)[1] + line1y + 10
        line3y = self.hanken_small_font.getsize(line3)[1] + line2y + 2
        line4y = self.hanken_small_font.getsize(line4)[1] + line3y + 2

        draw.text((0, self._status_bar_offset), line0, self.inky_display.BLACK, self.hanken_medium_font)
        draw.text((0, line0y), line1, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line1y), line2, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, line2y), line3, self.inky_display.BLACK, self.hanken_small_font)
        draw.text((0, line3y), line4, self.inky_display.BLACK, self.hanken_small_font)
        draw.text((0, line4y), line5, self.inky_display.BLACK, self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

    def rluCalibration(self, rlu_calibration_time, curr_rlu):
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        # self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        rlu_a = curr_rlu[0]
        rlu_b = curr_rlu[1]

        start_line = "> Press top button to start calibration."
        line = "RLU Calibration"
        line2 = f"This calibration will take {rlu_calibration_time}s"
        line3 = f"RLU A/B : {rlu_a:.3f}, {rlu_b:.3f}"
        return_line = "> Return to main menu"
        line1x, line1y = self.hanken_medium_font.getsize(line)
        line2x, line2y = self.hanken_medium_font.getsize(line2)
        line3x, line3y = self.hanken_small_font.getsize(line3)

        top_offset = height/2 - (line1y + line2y + line3y)/2
        x_pos1 = width/2 - line1x/2
        x_pos2 = width/2 - line2x/2
        x_pos3 = width/2 - line3x/2
        y_pos1 = top_offset
        y_pos2 = y_pos1 + line1y
        y_pos3 = y_pos2 + line2y

        draw.text((0, 0), start_line, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((x_pos1, y_pos1), line, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((x_pos2, y_pos2), line2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((x_pos3, y_pos3), line3, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, height - 20), return_line, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img.rotate(self.rotation_deg))
        self.inky_display.show()

if __name__ == "__main__":
    menu = Menu("STD", "OK")

    while True:
        userInput = input("Enter menu option: ")
        if userInput == str(0):
            menu.mainMenu([0, 1, 2, 3, 4])
        elif userInput == str(1):
            menu.measurementMenu()
        elif userInput == str(2):
            menu.showMeasurement(True, 1.1, 0.01, 0.9, 0.01, 30, 15)
        elif userInput == str(3):
            menu.statusMenu([1.2, 3.1, 2.2, 3.87, 4.99])
        elif userInput == str(4):
            menu.calibrationMenu("")
        elif userInput == str(5):
            menu.measurementInProgress(1.1, 0.01, 0.9, 0.01, 30, 15)
        elif userInput == str(6):
            menu.calibrationInProgress()
        elif userInput == str(7):
            menu.powerOff()
        elif userInput == str(8):
            menu.confirmCalibrationOverwrite()
        else:
            exit()