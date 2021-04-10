from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
import threading
import time
import concurrent.futures
from typing import List

# TODO: 
# - Implement logging

N_LINES = 4

class LumiScreenBusy(Exception):
    pass

class LumiScreen():
	def __init__(self):
		self._inky = InkyPHAT("black")
		self._smallFont = ImageFont.truetype(FredokaOne, 22)
		self._bigFont = ImageFont.truetype(FredokaOne, 32)
		self._busy = False
		self._lock = threading.Lock()

	def displayResult(self, sensorA:float = 0.0, sensorB:float = 0.0, sensorA_sem: float = 0.0, sensorB_sem: float = 0.0):
		# Displays two numerical measurements on the screen,
		# symmetrically about the center. Default behavior is
		# not to queue the display. 

		# sensorA: Float value from sensor A
		# sensorB: Float value from sensor B

		message = f"A: {sensorA:.4f} +/- {sensorA_sem}\nB:{sensorB:.4f}+/-{sensorB_sem}"
		self.displayMessage(message)

	def displayMessage(self, message):
		''' 
		Input 'message' is list of strings with maximum length of N_LINES, 
		corresponding to rows on the display.
		'''
		if not self._lock.locked():
			with self._lock:
				w, h = self._smallFont.getsize(message)
				x = (self._inky.WIDTH / 2) - (w / 2)
				y = (self._inky.HEIGHT / 2) - (h / 2)
				img = Image.new("P", (self._inky.WIDTH, self._inky.HEIGHT))
				draw = ImageDraw.Draw(img)
				draw.text((x, y), message, self._inky.BLACK, self._smallFont)
				self._inky.set_image(img.rotate(180))
				self._inky.show(True)
				#w, h = self._smallFont.getsize(message)
				# x = (self._inky.WIDTH / 2) - (w / 2)
				# y = (self._inky.HEIGHT / 2) - (h / 2)
				# x = 0
				# y = [self._inky.HEIGHT*x for x in range(N_LINES)]
				# img = Image.new("P", (self._inky.WIDTH, self._inky.HEIGHT))
				# draw = ImageDraw.Draw(img)
				# draw.text((x, y[0]), line1, self._inky.BLACK, self._smallFont)
				# draw.text((x, y[1]), line2, self._inky.BLACK, self._smallFont)
				# draw.text((x, y[2]), line3, self._inky.BLACK, self._smallFont)
				# draw.text((x, y[3]), line4, self._inky.BLACK, self._smallFont)

				self._inky.set_image(img.rotate(180))
				self._inky.show(message)

	def welcome(self):
		self.displayMessage('WELCOME!')

if __name__ == "__main__":
	screen = LumiScreen()

	try:
		with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
			for index in range(5):
				print(f"\nBefore message {index}")
				future = executor.submit(screen.displayMessage, f"Message {index}")
				print(f"After message {index}")
	except KeyboardInterrupt:
		pass