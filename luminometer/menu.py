#!/usr/bin/env python3
import enum
from os import stat
from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from font_intuitive import Intuitive
from inky.auto import auto
import numpy as np
from luminometer_constants import CUSTOM_CAL_A_NAME

class MenuStates(enum.Enum):
    MAIN_MENU = enum.auto()
    MEASUREMENT_MENU = enum.auto()
    MEASUREMENT_IN_PROGRESS = enum.auto()
    SHOW_FINAL_MEASUREMENT = enum.auto()
    STATUS_MENU = enum.auto()
    CALIBRATION_MENU = enum.auto()
    CALIBRATION_IN_PROGRESS = enum.auto()
    POWER_OFF = enum.auto()

class Menu():   
    def __init__(self, calibration, battery_status):
        try:
            self.inky_display = auto(ask_user=True, verbose=True)
        except TypeError:
            raise TypeError("You need to update the Inky library to >= v1.1.0")

        # inky_display.set_rotation(180)
        try:
            self.inky_display.set_border(self.inky_display.RED)
        except NotImplementedError:
            pass

        # Figure out scaling for display size
        scale_size = 1.0
        padding = 0

        if self.inky_display.resolution == (400, 300):
            scale_size = 2.20
            padding = 15

        if self.inky_display.resolution == (600, 448):
            scale_size = 2.20
            padding = 30

        if self.inky_display.resolution == (250, 122):
            scale_size = 1.30
            padding = -5
        
        self._status_bar_offset = 15
        self.selected_calibration = calibration
        self.battery_status = battery_status

        # Load the fonts
        self.intuitive_font = ImageFont.truetype(Intuitive, int(22 * scale_size))
        self.hanken_bold_font = ImageFont.truetype(HankenGroteskBold, int(35 * scale_size))
        self.hanken_medium_font = ImageFont.truetype(HankenGroteskMedium, int(16 * scale_size))
        self.hanken_small_font = ImageFont.truetype(HankenGroteskMedium, int(10 * scale_size))

        # self.mainMenu()

    def set_selected_calibration(self, calibration):
        self.selected_calibration = calibration
    def set_battery_status(self, battery_status):
        self.battery_status = battery_status

    def clearScreen(self):
        img = Image.new("P", self.inky_display.resolution)
        self.inky_display.set_image(img)
        self.inky_display.show()

    def screenSwitcher(self, **kwargs):
        state = kwargs["state"]

        # Display screens 
        if state == MenuStates.MAIN_MENU:
            self.set_battery_status(kwargs["battery_status"])
            self.set_selected_calibration(kwargs["selected_calibration"])
            self.mainMenu()

        elif state == MenuStates.MEASUREMENT_MENU:
            self.measurementMenu()

        elif state == MenuStates.MEASUREMENT_IN_PROGRESS:
            self.measurementInProgress(kwargs["measurementMode"], kwargs["time_elapsed"], kwargs["target_time"])

        elif state == MenuStates.SHOW_FINAL_MEASUREMENT:
            self.showMeasurement(kwargs["_measurementIsDone"], kwargs["resultA"], kwargs["semA"], kwargs["resultB"], 
                                    kwargs["semB"], kwargs["time_elapsed"])

        elif state == MenuStates.STATUS_MENU:
            self.statusMenu(kwargs["adc_vals"])

        elif state == MenuStates.CALIBRATION_MENU:
            self.calibrationMenu(kwargs["calA"])

        elif state == MenuStates.CALIBRATION_IN_PROGRESS:
            self.calibrationInProgress()

    def statusBar(self, draw):
        status = f"Cal: {self.selected_calibration} / Batt: {self.battery_status}"
        statusx, _ = self.hanken_small_font.getsize(status)
        x_pos = self.inky_display.resolution[0] - statusx
        draw.text((x_pos, 0), status, self.inky_display.BLACK, font=self.hanken_small_font)

    def mainMenu(self):
        self.clearScreen()

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        option1 = "> Start measurement"
        option2 = "> Status - OK" #TODO Change to update '- OK' dynamically
        option3 = "> Choose calibration"

        option1y = self.hanken_medium_font.getsize(option1)[1]
        option2y = self.hanken_medium_font.getsize(option2)[1]
        
        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, 2*option1y+self._status_bar_offset), option2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, 2*(option1y+option2y)+self._status_bar_offset), option3, self.inky_display.BLACK, font=self.hanken_medium_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def measurementMenu(self):
        self.clearScreen()

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        option1 = "> Autoexposure"
        option1_sub = "(HOLD 3s during measurement to abort)"
        option2 = "> Timed exposure"
        option2_sub = "(HOLD 1s=30s, 2s=60s, 3s=300s, 4s=600s)"
        option3 = "> Back to main"

        option1y = self.hanken_medium_font.getsize(option1)[1] + self._status_bar_offset
        option1suby = self.hanken_small_font.getsize(option1_sub)[1] + option1y
        option2y = self.hanken_medium_font.getsize(option2)[1] + option1suby
        option2suby = self.hanken_small_font.getsize(option2_sub)[1] + option2y
        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option1y), option1_sub, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option1suby), option2, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, option2y), option2_sub, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option2suby), option3, self.inky_display.BLACK, self.hanken_medium_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def calibrationInProgress(self):
        self.clearScreen()
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        line = "Calibration in progress"

        line1x, line1y = self.hanken_medium_font.getsize(line)

        draw.text((width/2 - line1x/2, height/2 - line1y/2), line, self.inky_display.BLACK, font=self.hanken_medium_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def measurementInProgress(self, measurement_type, time_elapsed, target_time=None):
        self.clearScreen()
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        target_time = str(target_time) + "s" if (target_time is not None) else "N/A"
        option1 = "Measurement in progress"
        option1_sub1 = f"{measurement_type}  Elapsed: {time_elapsed}s Target: {target_time}"
        option1_sub2 = "(Hold top button for 3s to abort)"

        option1x, option1y = self.hanken_medium_font.getsize(option1)
        option1xsub1, option1ysub1 = self.hanken_small_font.getsize(option1_sub1)
        option1xsub2, option1ysub2 = self.hanken_small_font.getsize(option1_sub2)

        draw.text((width/2 - option1x/2, height/2 - option1y), option1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((width/2 - option1xsub1/2, height/2), option1_sub1, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((width/2 - option1xsub2/2, height/2 + option1ysub1 + 20), option1_sub2, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def powerOff(self):
        self.clearScreen()
        
        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        # self.statusBar(draw)

        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]

        line = "POWERED OFF"

        line1x, line1y = self.hanken_medium_font.getsize(line)

        draw.text((width/2 - line1x/2, height/2 - line1y/2), line, self.inky_display.BLACK, font=self.hanken_medium_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def showMeasurement(self, final: bool=False, sensorA: float=0.0, sensorA_sem: float=0.0,
                            sensorB: float=0.0, sensorB_sem: float=0.0, duration_s: int=0):

        self.clearScreen()

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        line1 = "Final:" + ('Yes' if final == True else 'No') 
        line2 = f"A: {sensorA:.2f}+/-{sensorA_sem:.2f}"
        line3 = f"B: {sensorB:.2f}+/-{sensorB_sem:.2f}"
        line4 = f"Time: {int(duration_s):n} s"
        line5 = "> Clear and start new measurement"
        lines = [line1, line2, line3, line4]

        y_offset = 10
        for i, line in enumerate(lines):
            if i != 0:
                y_offset = y_offset + self.hanken_small_font.getsize(line)[1] + 5
            draw.text((0, y_offset), line, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, y_offset + self.hanken_small_font.getsize(line4)[1] + 20), line5, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def statusMenu(self, adc_vals):
        self.clearScreen()

        if len(adc_vals) < 5:
            print("Error: Too few ADC values")

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        yn_spaces = 20
        adc_spaces = 35
        line1 = "Low Battery:"
        line2 = "34V in range:"
        line3 = "PBias in range:"
        line4 = "CRC Err:"
        line5 = "H-Bridge Err:"
        line6 = "> Click to return to main menu"
        lines = [line1, line2, line3, line4, line5]
        for i, line in enumerate(lines):
            # Need a weird band-aid fix so CRC aligns
            if "CRC" in line:

                line = line + " "*(4+yn_spaces-len(line)) + "Y/N"
                lines[i] = line + " "*(4+adc_spaces-len(line)) + f"ADC {i+1}:     {adc_vals[i]}"
            else:
                line = line + " "*(yn_spaces-len(line)) + "Y/N"
                lines[i] = line + " "*(adc_spaces-len(line)) + f"ADC {i+1}:     {adc_vals[i]}"
        
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
        draw.text((0, line5y+20), line6, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def calibrationMenu(self, calibrationA_name):
        self.clearScreen()

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        option1 = "> Restore standard (default) calibration"
        option2 = f"> Custom calibration A: {calibrationA_name}"
        
        subtext = "- Choose any option to return to main"
        subtext2 = "- HOLD 5s middle/bottom buttons to"
        subtext3 = "  overwrite custom calibration"

        option_offset = 5
        
        option1y = self._status_bar_offset + self.hanken_small_font.getsize(option1)[1] + option_offset
        option2y = option1y + self.hanken_small_font.getsize(option2)[1] + 25
        sub1y = option2y + self.hanken_small_font.getsize(subtext)[1]
        sub2y = sub1y + self.hanken_small_font.getsize(subtext2)[1]

        draw.text((0, self._status_bar_offset), option1, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option1y), option2, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, option2y), subtext, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, sub1y), subtext2, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, sub2y), subtext3, self.inky_display.BLACK, font=self.hanken_small_font)

        self.inky_display.set_image(img)
        self.inky_display.show()

    def confirmCalibrationOverwrite(self):
        self.clearScreen()

        img = Image.new("P", self.inky_display.resolution)
        draw = ImageDraw.Draw(img)
        self.statusBar(draw)

        line1 = "This will overwrite your existing custom calibration. Are you sure?"
        line2 = "> YES (top button)"
        line3 = "---"
        line4 = "NO (bottom button)"
        
        width = self.inky_display.resolution[0]
        height = self.inky_display.resolution[1]
        line1x, line1y = self.hanken_medium_font.getsize(line1)
        line2x, line2y = self.hanken_small_font.getsize(line2)
        line3x, line3y = self.hanken_small_font.getsize(line3) + line2y
        
        draw.text((width - line1x/2, height/2 - line1y/2), line1, self.inky_display.BLACK, font=self.hanken_medium_font)
        draw.text((0, height/2), line2, self.inky_display.BLACK, font=self.hanken_small_font)
        draw.text((0, height/2 + line2y), line3, self.inky_display.BLACK, self.hanken_small_font)
        draw.text((0, height/2 + line3y), line4, self.inky_display.BLACK, self.hanken_small_font)

        self.inky_display.set_image(img)
        self.inky_display.show()


    def displayOptions(self):
        for state, member in MenuStates.__members__.items():
            print(f"State: {state} - {member.value}")

if __name__ == "__main__":
    menu = Menu("STD", "OK")

    while True:
        menu.displayOptions()
        userInput = input("Enter menu option: ")
        if userInput == str(0):
            menu.mainMenu()
        elif userInput == str(1):
            menu.measurementMenu()
        elif userInput == str(2):
            menu.showMeasurement(True, 1.1, 0.01, 0.9, 0.01, 30)
        elif userInput == str(3):
            menu.statusMenu([1.2, 3.1, 2.2, 3.87, 4.99])
        elif userInput == str(4):
            menu.calibrationMenu(CUSTOM_CAL_A_NAME)
        elif userInput == str(5):
            menu.measurementInProgress("TIMED", 10, 30)
        elif userInput == str(6):
            menu.calibrationInProgress()
        elif userInput == str(7):
            menu.powerOff()
        elif userInput == str(8):
            menu.confirmCalibrationOverwrite()
        else:
            exit()