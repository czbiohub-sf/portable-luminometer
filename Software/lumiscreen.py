from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
import threading, queue
import time
import concurrent.futures
from dataclasses import dataclass, field


# TODO: 
# - Implement logging

class LumiScreenBusy(Exception):
    pass

class LumiScreen():
	def __init__(self):
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
		self._displayMessage(message)

	def _displayMessage(self, message):
		with self._lock:
			w, h = self._smallFont.getsize(message)
			x = (self._inky.WIDTH / 2) - (w / 2)
			y = (self._inky.HEIGHT / 2) - (h / 2)
			img = Image.new("P", (self._inky.WIDTH, self._inky.HEIGHT))
			draw = ImageDraw.Draw(img)
			draw.text((x, y), message, self._inky.BLACK, self._smallFont)
			self._inky.set_image(img.rotate(180))
			self._inky.show(message)

	def queueMessage(self, message: str, queue: bool = False):
		'''
		Since the inky pHat is so slow to refresh, a message queue is created
		in order to handle multiple incoming display requests.

		message: Message to be displayed
		queue: Boolean flag indicating what to do if the screen is busy. Setting
		this to 'True' will add the message to a FIFO queue.
		'''
		if (queue == False) and self._lock.locked():
				print("LumiScreen busy and message not queued.")

		else:
			with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
				try:
					future = executor.submit(self._displayMessage, message)
				except Exception as exc:
					print(f'LumiScreen generated an exception: {exc}')
					raise exc

	def welcome(self):
		self.queueMessage('WELCOME!')

if __name__ == "__main__":
	screen = LumiScreen()
	screen.welcome()
	for index in range(3):
		start = time.time()
		screen.queueMessage(f"Message {index}", False)
		print(f"Elapsed time: {time.time()-start}")
		print(f'Queued message {index}')
