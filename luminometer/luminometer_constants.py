# Sampling rate of the ADC (488 kHz CLKIN, OSR = 4096, global chop mode. See ADS131m08 datasheet 8.4.2.2)
SAMPLE_TIME_S = 0.050
SHUTTER_ACTUATION_TIME = 0.03
SHUTTER_PERIOD = 1
RLU_PER_V = 20000
SKIP_SAMPLES = 3
BTN_1_HOLD_TO_POWERDOWN_S = 3
BUZZ_S = 0.3
DEF_DARK_TIME = 600
MAX_EXPOSURE = 3000
MIN_SNR = 5
DEF_AUTO_MAX_DURATION = 10000

# BCM pins
# Luminometer pushbuttons
BTN_1 = 3
BTN_2 = 26
BTN_3 = 19

# H-bridge inputs (channel A)
AIN1 = 16
AIN2 = 13
# H-bridge inputs (channel B)
BIN1 = 5
BIN2 = 6
# H-bridge logical I/O
NSLEEP = 1
NFAULT = 0

# Audio element
BUZZ = 12
FREQ = 4000

# SPI Device number
SPI_CE = 1

# ADC Data ready pin
DRDY = 15
