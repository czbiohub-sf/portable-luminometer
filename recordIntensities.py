# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import csv

filename = 'file1.csv'

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 1
camera.shutter_speed = 1000000
camera.exposure_mode = 'off'
camera.awb_mode = 'off'
camera.iso = 100

rawCapture = PiRGBArray(camera, size=(640, 480))

signal = []
integratedSignal = []

# allow the camera to warmup
time.sleep(0.1)

with open(filename, 'w', newline='') as csvfile:
    lightWriter = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)

	# capture frames from the camera
	for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
		# grab the raw NumPy array representing the image, then initialize the timestamp
		# and occupied/unoccupied text
		image = frame.array

		# Compute mean of the entire frame
		imageMean = image.mean()

		# Print to command line
		print(str(imageMean))

		# Append to signal and integrated signal lists
		signal.append(imageMean)
		integratedSignal.append(integratedSignal[-1] + imageMean)
		
		# Write values to a spreadsheet
		lightWriter.writerow([imageMean, integratedSignal[-1]])


		# show the frame
		cv2.imshow("Frame", image)
		key = cv2.waitKey(1) & 0xFF
		# clear the stream in preparation for the next frame
		rawCapture.truncate(0)
		# if the `q` key was pressed, break from the loop
		if key == ord("q"):
			break