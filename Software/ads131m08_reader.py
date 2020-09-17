#! /usr/bin/env python3
"""
Application Notes:

    1. The ADS has can take a bits-per-word length of 16, 24, or 32.
       Raspberry Pis are only configured tor 8 bits per word. Therefore, we
       just send each byte in every word individually.
    2. Reading data after a pause: see 8.5.1.9.1
"""

import spidev
import RPi.GPIO as GPIO

from adc_reader import ADCReader


# Set gpio pin numbering to the gpio pin numbers on the raspberry pi
GPIO.setmode(GPIO.BOARD)


# Commands (ADS131M08 datasheet 8.5.1.10)
WREG_OPCODE = 0b0110000000000000
RREG_OPCODE = 0b1010000000000000
UNLOCK_OPCODE = 0b0000011001010101
LOCK_OPCODE = 0b0000010101010101
WAKEUP_OPCODE = 0b0000000000110011
STANDBY_OPCODE = 0b0000000000100010
RESET_OPCODE = 0b0000000000010001
NULL_OPCODE = 0b0000000000000000


# Register adresses
ID_ADDR = 0x00
STATUS_ADDR = 0x01
MODE_ADDR = 0x02
CLOCK_ADDR = 0x03
CFG_ADDR = 0x06


# Register Payloads
# clock register
ALL_CH_DISABLE_MASK = 0b0
ALL_CH_ENABLE_MASK = 0b11111111 << 8
OSR_16256_MASK = 0b111 << 2
# The datasheet is a little confusing with regards to the chrystal oscillator
# For the luminometer design, we give the ADC the SCLK from the master SPI.
# Therefore, we enable the XTAL_OSC_DISABLE bit of the clock register
# I found this a little unclear, see the link from the chip developer below
# https://e2e.ti.com/support/data-converters/f/73/t/905809
XTAL_OSC_DISABLE_MASK = 0b1 << 7
EXTERNAL_REF_MASK = 0b0
PWR_HIGH_RES_MASK = 0b11
# mode register
RESET_MASK = 0b0 << 10
WLEN_24_MASK = 0b01 << 8
SPI_TIMEOUT_MASK = 0b1 << 4
DRDY_FMT_PULSE_MASK = 0b1
DRDY_FMT_LOW_MASK = 0b1
# cgf register
GLOBAL_CHOP_EN_MASK = 0b1 << 8
DEFAULT_CHOP_DELAY_MASK = 0b0011 << 9


class ADS131M09Reader(ADCReader):
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.ads_num_frame_words: int = 10  # Num. words in full ADS131 frame
        self.ads_bits_per_word: int = 24  # default word length on ADS
        self.rpi_bits_per_word: int = 8  # only available word length on RPi
        self.bytes_per_word: int = int(self.ads_bits_per_word / self.rpi_bits_per_word)

        self._DRDY: int = 37  # drdy pin is 37
        self._first_read: bool = True

        GPIO.setup(self._DRDY, GPIO.IN)

    def setup_adc(self, bus, device):
        self.spi.open(bus, device)

        # ADS131M09 Settings
        self.spi.mode = 0b01
        self.spi.max_speed_hz = int(1e6)
        self.spi.no_cs = True  # We tied the ~CS to GND

    def read(self):
        if self._first_read:
            res = self.spi.xfer([0b0] * self.ads_num_frame_words * self.bytes_per_word)
            self._first_read = False
        res = self.spi.xfer([0b0] * self.ads_num_frame_words * self.bytes_per_word)
        # Combine the bytes back into words before returning
        return [self._combine_bytes(*res[i:i + self.bytes_per_word]) for i in range(0, len(res), self.bytes_per_word)]

    def adc_register_write(self, register_addr: bytes, data: bytes):
        """
        params
                register_addr:     16-bit register address mask
                data:              data to write

        The ADS write command is 0b011a aaaa annn nnnn, where a aaaa a is the
        address of the register, and nnn nnnn is the number of consecutive registers
        to write to, minus 1.
        Therefore, we shift the register address left by 7
        """
        shift_value = self.ads_bits_per_word - 16
        register_shift = 7

        shifted_data_payload = [*(data << shift_value).to_bytes(self.bytes_per_word, "big")]
        cmd = (WREG_OPCODE | register_addr << register_shift | len(shifted_data_payload)) << shift_value
        cmd_payload = [*cmd.to_bytes(self.bytes_per_word, "big")]

        self.spi.writebytes(cmd_payload)
        self.spi.writebytes(shifted_data_payload)

    def data_ready(self):
        return GPIO.input(adc_reader._DRDY)

    def _combine_bytes(self, *byte_args):
        """
        takes some sequence of bytes, does the appropriate
        bit shifts and returns the combined int

        >>> _combine_bytes(0b01, 0b01)
        0000000100000001    
        """
        out = 0
        num_bytes = len(byte_args)
        for i in range(num_bytes):
            out |= byte_args[num_bytes - i - 1] << (8 * (num_bytes - i - 1))
        return out

if __name__ == "__main__":
    adc_reader = ADS131M09Reader()
    adc_reader.setup_adc(0, 1)

    # wait for DRDY to go high, indicating the ADC has started up
    while not GPIO.input(adc_reader._DRDY):
        print("not ready")
    print("ready")

    CH_2_3_MASK = ALL_CH_DISABLE_MASK | 1 << (8 + 2) | 1 << (8 + 3)

    # Disable all channels so short frames can be written during config phase
    adc_reader.adc_register_write(CLOCK_ADDR, ALL_CH_DISABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK)
    # print('CLOCK WRITE', '{0:b}'.format(ALL_CH_DISABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK))

    # Clear reset flag, mmake DRDY active low, use 24 bit word length, & use a SPI Timeout
    adc_reader.adc_register_write(MODE_ADDR, RESET_MASK | DRDY_FMT_LOW_MASK | WLEN_24_MASK | SPI_TIMEOUT_MASK)
    # print('MODE WRITE', '{0:b}'.format(RESET_MASK | DRDY_FMT_PULSE_MASK | WLEN_24_MASK | SPI_TIMEOUT_MASK))

    # Enable Global Chop Mode, and rewrite default chop delay
    adc_reader.adc_register_write(CFG_ADDR, GLOBAL_CHOP_EN_MASK | DEFAULT_CHOP_DELAY_MASK)
    # print('CFG WRITE', '{0:b}'.format(GLOBAL_CHOP_EN_MASK | DEFAULT_CHOP_DELAY_MASK))

    # Enable channels 2 and 3, and rewrite other desired settings
    adc_reader.adc_register_write(CLOCK_ADDR, CH_2_3_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK)
    # print('CLOCK WRITE', '{0:b}'.format(CH_2_3_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK))

    while 1:
        adc_reader.read()
