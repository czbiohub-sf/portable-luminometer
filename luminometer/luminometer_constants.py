# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050
SKIP_SAMPLES = 3
BTN_1_HOLD_TO_POWERDOWN_S = 3
BTN_1_HOLD_TO_CALIBRATE_S = 10
BUZZ_S = 0.02
DEF_DARK_TIME = 1800
MAX_EXPOSURE = 3000
MIN_SNR = 7
MIN_PERIODS = 7
DEF_AUTO_MAX_DURATION = 10000
RLU_PER_V = 20000


# Thermal calibration file location
CAL_PATH = "/home/pi/Documents/ulc-tube-reader/luminometer/temp_coeffs.json"

# Calibrated values
SENSOR_A_DARK_V = -0.42978502
SENSOR_B_DARK_V = -0.4290032
SENSOR_A_CP_RATIO = 0.0003
SENSOR_B_CP_RATIO = 0.0003
ADD_OFFSET_RLU = 0.5

# BCM pins
BTN_1 = 18
BTN_2 = 3
BTN_3 = 2
FAN = 20
PMIC_LBO = 21
ADC_PWR_EN = 16

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

# Custom names for calibrations shown int he menu
CUSTOM_CAL_A_NAME = "Blood"
CUSTOM_CAL_B_NAME = "Serum"