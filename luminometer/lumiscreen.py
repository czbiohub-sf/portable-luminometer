from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
import threading
import time
import concurrent.futures
from typing import List
from enum import Enum, auto

# TODO: 
# - Implement logging

N_DISPLAY_LINES = 4

class LumiMode(Enum):
	TITLE = auto()
	RESULT = auto()
	READY = auto()

class LumiScreenBusy(Exception):
    pass

class LumiScreen():
	def __init__(self, rotation_deg: int = 0):
		self._inky = InkyPHAT("black")
		self._smallFont = ImageFont.truetype(FredokaOne, 22)
		self._bigFont = ImageFont.truetype(FredokaOne, 32)
		self._rotation_deg = rotation_deg
		self._busy = False
		self._lock = threading.Lock()

	def parser(self, displayMode: LumiMode, *args, **kwargs):

		if displayMode == LumiMode.TITLE:
			self.displayTitle(*args, **kwargs)

		elif displayMode == LumiMode.RESULT:
			self.displayResult(*args, **kwargs)

		elif displayMode == LumiMode.READY:
			self.displayReady(*args, **kwargs)

		else:
			print("Display mode not recognized")

		return


	def displayResult(self, \
		dark: bool = False, \
		final: bool = False, \
		sensorA: float = 0.0,  \
		sensorA_sem: float = 0.0, \
		sensorB: float = 0.0, \
		sensorB_sem: float = 0.0, \
		duration_s: int = 0):

		'''
		Displays a measurement result, either in-progress (final == False) or completed
		(finale == True). 

		dark: bool, indicating whether a dark measurement has been performed
		final: bool, indicating whether the measurement has completed or not
		sensorA: Float value from sensor A
		sensorA_sem: Float value for the errorbar for sensor A (s.e.m.)
		sensorB: Float value from sensor B
		sensorB_sem: Float value for the errorbar for sensor B (s.e.m.)
		duration_s: int
		'''
		message = 4*[None]
		message[0] = "Final:" + ('Yes' if final == True else 'No') 
		message[1] = f"A: {sensorA:.2f}+/-{sensorA_sem:.2f}"
		message[2] = f"B: {sensorB:.2f}+/-{sensorB_sem:.2f}"
		message[3] = f"Time: {int(duration_s):n} s"

		self._displayLines(message)

	def displayReady(self, dark: bool = False):
		
		'''
		Displays a screen indicating that the device is ready to start a measurement.
		dark: bool, indicating whether a dark measurement has been performed
		'''
		message = 4*[None]
		message[0] = "READY" #+ "  Dark:" + ('Yes' if dark == True else 'No')
		message[1] = "Top: Auto"
		message[2] = "10/30/60/300/600"
		message[3] = "Bottom: CAL/OFF"

		self._displayLines(message)

	def _displayLines(self, messageList:List[str] = ['']):
		''' 
		Input 'message' is list of strings with maximum length of N_DISPLAY_LINES, 
		corresponding to max number of rows on the display.

		This is the only method allowed to access the _inky.show() method,
		in order to protect the hardware resource (thread-locked).

		Inputs:
		messageList: A list of strings of maximum length N_DISPLAY_LINES
		'''

		if not self._lock.locked():
			with self._lock:
				if len(messageList) > N_DISPLAY_LINES:
					print(f"Too many entries! Using the first {N_DISPLAY_LINES}.")
					messageList = messageList[0:N_DISPLAY_LINES]

				_, h = self._smallFont.getsize('a')
				xOffset = 5
				yOffset = 5
				gap = 1
				img = Image.new("L", (self._inky.WIDTH, self._inky.HEIGHT))
				draw = ImageDraw.Draw(img)

				for i,text in enumerate(messageList):
					rowPos = yOffset + round(i*(h+gap))
					draw.text((xOffset, rowPos), messageList[i], self._inky.BLACK, self._smallFont)
				self._inky.set_image(img.rotate(self._rotation_deg))
				self._inky.show(True)

	def displayTitle(self, title:str = ''):
		if not self._lock.locked():
			with self._lock:
				w, h = self._smallFont.getsize(title)
				x = (self._inky.WIDTH / 2) - (w / 2)
				y = (self._inky.HEIGHT / 2) - (h / 2)
				img = Image.new("P", (self._inky.WIDTH, self._inky.HEIGHT))
				draw = ImageDraw.Draw(img)
				draw.text((x, y), title, self._inky.BLACK, self._smallFont)
				self._inky.set_image(img.rotate(self._rotation_deg))
				self._inky.show(True)

if __name__ == "__main__":
	screen = LumiScreen(180)
	screen.displayResult(True, True, 15000, 300, 500, 100, 3000) 
	# try:
	# 	with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
	# 		for index in range(3):
	# 			print(f"\nBefore message {index}")
	# 			future = executor.submit(screen.displayMessage, f"Message {index}")
	# 			print(f"After message {index}")
	# except KeyboardInterrupt:
	# 	pass