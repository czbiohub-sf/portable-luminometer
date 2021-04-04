from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
import threading
import time
import concurrent.futures

# TODO: 
# - Implement logging

class LumiScreenBusy(Exception):
    pass

class LumiScreen():
	def __init__(self, executor):
		self._inky = InkyPHAT("black")
		self._smallFont = ImageFont.truetype(FredokaOne, 22)
		self._bigFont = ImageFont.truetype(FredokaOne, 32)
		self._busy = False
		self._lock = threading.Lock()

	def displayResult(self, sensorA:float, sensorB:float):
		# Displays two numerical measurements on the screen,
		# symmetrically about the center. Default behavior is
		# not to queue the display. 

		# sensorA: Float value from sensor A
		# sensorB: Float value from sensor B

		message = f"{sensorA:.4f} \t {sensorB:.4f}"
		self.displayMessage(message)

	def displayMessage(self, message):
		with self._lock:
			w, h = self._smallFont.getsize(message)
			x = (self._inky.WIDTH / 2) - (w / 2)
			y = (self._inky.HEIGHT / 2) - (h / 2)
			img = Image.new("P", (self._inky.WIDTH, self._inky.HEIGHT))
			draw = ImageDraw.Draw(img)
			draw.text((x, y), message, self._inky.BLACK, self._smallFont)
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