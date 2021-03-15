from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
import RPi.GPIO as GPIO


class LumiScreen():
	def __init__(self):
		self._inkyphat = InkyPHAT("black")
		self._smallFont = ImageFont.truetype(FredokaOne, 22)
		self._bigFont = ImageFont.truetype(FredokaOne, 32)

	def displayResult(self, sensorA:float, sensorB:float):
		message = f"{sensorA:.4f} \t {sensorB:.4f}"
		self.displayMessage(message)


	def displayMessage(self, message):
		w, h = self._smallFont.getsize(message)
		x = (self._inkyphat.WIDTH / 2) - (w / 2)
		y = (self._inkyphat.HEIGHT / 2) - (h / 2)
		img = Image.new("P", (self._inkyphat.WIDTH, self._inkyphat.HEIGHT))
		draw = ImageDraw.Draw(img)
		draw.text((x, y), message, self._inkyphat.BLACK, self._smallFont)
		self._inkyphat.set_image(img.rotate(180))
		self._inkyphat.show()

	def welcome(self):
		message = 'WELCOME'
		self.displayMessage(message)
