#! /usr/bin/env python3

from ads131m08_reader import ADS131M08Reader

from PIL import Image, ImageFont, ImageDraw
from font_fredoka_one import FredokaOne

from inky import InkyPHAT
import RPi.GPIO as GPIO


if __name__ == "__main__":
    device = 1  # using CE1
    # default channels are channels 2,3
    adc_reader = ADS131M08Reader()
    adc_reader.setup_adc(device)

    inkyphat = InkyPHAT("black")
    font = ImageFont.truetype(FredokaOne, 22)

    d1 = d2 = 0.0

    def cb(channel):
        global d1, d2
        data = adc_reader.read()
        d1, d2 = data[2], data[3]

    GPIO.add_event_detect(adc_reader._DRDY, GPIO.FALLING, callback=cb)

    try:
        while True:
            message = f"{d1:.3} \t {d2:.3}"
            print(message)
            w, h = font.getsize(message)
            x = (inkyphat.WIDTH / 2) - (w / 2)
            y = (inkyphat.HEIGHT / 2) - (h / 2)
            img = Image.new("P", (inkyphat.WIDTH, inkyphat.HEIGHT))
            draw = ImageDraw.Draw(img)
            draw.text((x, y), message, inkyphat.BLACK, font)
            inkyphat.set_image(img)
            inkyphat.show()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
