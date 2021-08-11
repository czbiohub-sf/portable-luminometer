# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050
SKIP_SAMPLES = 3
BTN_1_HOLD_TO_POWERDOWN_S = 3
BTN_1_HOLD_TO_CALIBRATE_S = 10
BUZZ_S = 0.02
DEF_DARK_TIME = 1800
SENSITIVITY_NORM_TIME = 30
MAX_EXPOSURE = 3000
MIN_SNR = 7
MIN_PERIODS = 7
DEF_AUTO_MAX_DURATION = 10000


# Thermal calibration file location
STANDARD_CAL_PATH = "/home/pi/Documents/ulc-tube-reader/luminometer/temp_coeffs.json"
CUSTOM_CAL_A_PATH = "/home/pi/Documents/ulc-tube-reader/luminometer/temp_coeffs_A.json"
CUSTOM_CAL_NAME = "Custom"

# Last chosen calibration
LAST_CAL = "/home/pi/Documents/ulc-tube-reader/luminometer/last_chosen_cal.json"

# RLU calibration location
RLU_CAL_PATH = "/home/pi/Documents/ulc-tube-reader/luminometer/rlu.json"

# Screen type location
SCREEN_TYPE_PATH = "/home/pi/Documents/ulc-tube-reader/luminometer/screen_type.json"

# Log and measurement csv output directories
LOG_OUTPUT_DIR = "/home/pi/luminometer-logs/"
MEASUREMENT_OUTPUT_DIR = "/home/pi/measurements/"
ALL_MEASUREMENTS_CSV_FILENAME = "all-measurements.csv"

# Calibrated values
SENSOR_A_DARK_V = -0.42978502
SENSOR_B_DARK_V = -0.4290032
SENSOR_A_CP_RATIO = 0.0003
SENSOR_B_CP_RATIO = 0.0003

# RLU calibration parameters
TARGET_RLU = 1000
ADD_OFFSET_RLU = 0.5

# BCM pins
BTN_1 = 18
BTN_2 = 3
BTN_3 = 2
FAN = 20
PMIC_LBO = 21
ADC_PWR_EN = 16

# Map button channel to physical position on the box
BTN_PIN_TO_POS = {
    BTN_1: "Bottom",
    BTN_2: "Middle",
    BTN_3: "Top"
}

# Shutter parameters
SHUTTER_ACTUATION_TIME = 0.15
SHUTTER_PERIOD = 1
SHUTTER_DRIVE_DR = 1000000
SHUTTER_HOLD_DR = 500000
SHT_1 = 24
SHT_PWM = 12
SHT_PWM_FREQ = 50000

# H-bridge logical I/O
NSLEEP = 23
SHT_FAULT = 14

# Cooling
COOL_PWM = 13

# Audio element
BUZZ = 25

# SPI Device number
SPI_CE = 1

# ADC Data ready pin
DRDY = 15

# Map button held duration to exposure time 
DURATION_TO_EXPOSURE = {
    0: 10,
    1: 30,
    2: 60,
    3: 300,
    4: 600
}

# Hard-coded delay (in seconds) for the newer InkyPHAT screens
# (which seem to return too early from their "_busy_wait()" function)
SCREEN2_DELAY = 5

# Special button combo secrets
RLU_CALIBRATION_COMBO = [BTN_3, BTN_2, BTN_3, BTN_2]

# Duration to hold bottom button to power off
POWER_OFF_DURATION = 5

# Duration to hold top button to abort during a measurement
ABORT_MEASUREMENT_DURATION = 3

# Duration to hold button to initiate moving to a new screen (0 is a tap)
TRANSITION_DURATION = 0

# Time to hold button to initiate a calibration when in the appropriate menu
HOLD_TO_CALIBRATE_TIME = 5