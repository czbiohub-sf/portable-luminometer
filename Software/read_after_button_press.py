#! /usr/bin/env python3
""" Simple program to read the luminometer sensors for N seconds, after a delay of M seconds.

-- Important Links --

Datasheet
	https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1601338573920

-- Application Notes --

The SPI communication is done completely in 10-word frames (see 8.5.1.7 of the datasheet for information on this). Each
word can be 2, 3, or 4 bytes (i.e. 16, 24, or 32 bits). The Raspberry Pi can only communicate 1-byte words. Therefore,
if you were to attempt to send an integer which is outside the range of one byte, you would get an OS Error. This means
we must split our words into individual bytes (which is done in our code by the int.to_bytes method). Since ADC data is
24 bits (8.5.1.9), we will use 24-bit (3 byte) words.
Communication words also have specific format that is worth knowing. Quoting from 8.5.1.8 SPI Communication Words:

"The device defaults to a 24-bit word size. Commands, responses, CRC, and registers always contain 16 bits of actual
data. These words are always most significant bit (MSB) aligned, and therefore the least significant bits (LSBs) are
zero-padded to accommodate 24- or 32-bit word sizes."

So in short, each of our words that we receive or send which are only 16 bytes long are zero-padded on the right.
So if 'd' signifies a data bit, each word of commands, responses, CRC, and registers have the format (spaces
added for clarity)

	dddd dddd dddd dddd 0000 0000

This is responsible for some bit shifting which occurs throughout the document.
"""

import time
import csv
import argparse
import RPi.GPIO as GPIO

from consts import *
from ads131m08_reader import ADS131M08Reader, bytes_to_readable


# Device user input pushbuttons, BCM pins
BTN_1 = 13
BTN_2 = 19
BTN_3 = 26

# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050

if __name__ == "__main__":

	# Parse command line args
	parser = argparse.ArgumentParser()
	parser.add_argument('--delay', '-d', type=int, required=True, help="Delay time in seconds")
	parser.add_argument('--integration', '-i', type=int, required=True, help="Integration time in seconds")
	parser.add_argument('--title','-t',type=str, required=True, help="Title for output file (no extension)")
	args, _ = parser.parse_known_args()

	delayTime_seconds = args.delay
	integrationTime_seconds = args.integration
	title = args.title

	n_samples = int(integrationTime_seconds/SAMPLE_TIME_S)

	device = 1  # using CE1
	adc_reader = ADS131M08Reader()
	adc_reader.setup_adc(device, channels=[0,1])

	print("ID")
	d = adc_reader.read_register(ID_ADDR)
	print(bytes_to_readable(d)[0])
	print()

	print("MODE")
	d = adc_reader.read_register(MODE_ADDR)
	print(bytes_to_readable(d)[0])
	print()

	print("CLOCK")
	d = adc_reader.read_register(CLOCK_ADDR)
	print(bytes_to_readable(d)[0])
	print()

	print("CFG")
	d = adc_reader.read_register(CFG_ADDR)
	print(bytes_to_readable(d)[0])
	print()

	print("STATUS")
	d = adc_reader.read_register(STATUS_ADDR)
	print(bytes_to_readable(d)[0])
	print()

	errs = sc = d1 = d2 = 0

	with open(title + '.csv', 'w', newline='') as csvFile:
		csvWriter = csv.writer(csvFile)

		def cb(channel):
			global sc, csvWriter, errs
			sc += 1
			try:
				d = adc_reader.read()
				csvWriter.writerow(d)
			except CRCError:
				errs += 1
				return
			print(f"CH0: {d[0]} \t CH1: {d[1]}")

		GPIO.add_event_detect(adc_reader._DRDY, GPIO.FALLING, callback=cb)

		# Wait for button-press,then wait a delay before starting the measurement
		GPIO.setup(BTN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.wait_for_edge(BTN_1, GPIO.FALLING)
		print(f'Button pressed. Waiting for {delayTime_seconds} seconds...')
		time.sleep(delayTime_seconds)

		t0 = time.time()
		try:
			while sc < n_samples:
				pass
		except KeyboardInterrupt:
			pass
		finally:
			t1 = time.time()
			GPIO.cleanup()

	print(f"\n{sc} samples in {t1 - t0:.5} seconds. Sample rate of {sc / (t1 - t0)} Hz")
	print(f"{errs} CRC Errors encountered.")
