"""
Constants for the ads131m08 ADC
"""

# Commands (Datasheet 8.5.1.10)
WREG_OPCODE = 0b0110000000000000
RREG_OPCODE = 0b1010000000000000
UNLOCK_OPCODE = 0b0000011001010101
LOCK_OPCODE = 0b0000010101010101
WAKEUP_OPCODE = 0b0000000000110011
STANDBY_OPCODE = 0b0000000000100010
RESET_OPCODE = 0b0000000000010001
NULL_OPCODE = 0b0000000000000000


# Register adresses (Datasheet 8.6)
ID_ADDR = 0x00
STATUS_ADDR = 0x01
MODE_ADDR = 0x02
CLOCK_ADDR = 0x03
CFG_ADDR = 0x06
REGMAP_CRC_ADDR = 0x3E


# Register Payloads (Datasheet 8.6)
# clock register
ALL_CH_DISABLE_MASK = 0b00000000 << 8
ALL_CH_ENABLE_MASK = 0b11111111 << 8
CH_2_3_ENABLE_MASK = 0b00001100 << 8
OSR_16256_MASK = 0b111 << 2
OSR_8192_MASK = 0b110 << 2
OSR_4096_MASK = 0b101 << 2
# The datasheet is a bit confusing with regards to the chrystal oscillator.
# For the luminometer design, we give the ADC a GPCLK signal
# Therefore, we enable the XTAL_OSC_DISABLE bit of the clock register
# I found this a bit unclear, see the link from the chip developer below
# https://e2e.ti.com/support/data-converters/f/73/t/905809
XTAL_OSC_DISABLE_MASK = 0b1 << 7
EXTERNAL_REF_MASK = 0b0 << 6
PWR_HIGH_RES_MASK = 0b11

# mode register
REG_CRC_EN_MASK = 0b1 << 13
RX_CRC_EN_MASK = 0b1 << 12
RESET_MASK = 0b1 << 10
CLEAR_RESET_MASK = 0b0 << 10
WLEN_24_MASK = 0b01 << 8
SPI_TIMEOUT_MASK = 0b1 << 4
DRDY_HIZ_OPEN_COLLECT = 0b1 << 1
DRDY_FMT_PULSE_MASK = 0b1
DRDY_FMT_LOW_MASK = 0b0

# cgf register
GLOBAL_CHOP_EN_MASK = 0b1 << 8
DEFAULT_CHOP_DELAY_MASK = 0b0011 << 9


# Assorted masks
# bit is set in Status register if there was a CRC error on the previous
# input command
STATUS_CRC_ERR = 0b1 << 12
