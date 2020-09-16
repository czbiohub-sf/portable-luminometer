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
WREG_OPCODE    = 0b0110000000000000
RREG_OPCODE    = 0b1010000000000000
UNLOCK_OPCODE  = 0b0000011001010101
LOCK_OPCODE    = 0b0000010101010101
WAKEUP_OPCODE  = 0b0000000000110011
STANDBY_OPCODE = 0b0000000000100010
RESET_OPCODE   = 0b0000000000010001
NULL_OPCODE    = 0b0000000000000000


# Register adresses
ID_ADDR = 0x00
STATUS_ADDR = 0x01
MODE_ADDR = 0x02
CLOCK_ADDR = 0x03


# Register Payloads

# clock register
ALL_CH_DISABLE_MASK   = 0b0000000000000000
ALL_CH_ENABLE_MASK    = 0b1111111100000000
OSR_16256_MASK        = 0b0000000000011100
XTAL_OSC_DISABLE_MASK = 0b0000000010000000
EXTERNAL_REF_MASK     = 0b0000000001000000
PWR_HIGH_RES_MASK     = 0b0000000000000011

# mode register
RESET_MASK = 1 << 10
WLEN_24_MASK = 1 << 8
SPI_TIMEOUT_MASK = 1 << 4



class ADS131M09Reader(ADCReader):

    def __init__(self):
        self.spi = spidev.SpiDev()
        self.ads_num_frame_words: int = 10  # Num. words in full ADS131 frame
        self.ads_bits_per_word: int = 24  # default word length on ADS
        self.rpi_bits_per_word: int = 8   # only available word length on RPi
        self.bytes_per_word: int = int(self.ads_bits_per_word / self.rpi_bits_per_word)

        self._DRDY: int = 37  # drdy pin is 37
        self._first_read: bool = True

        GPIO.setup(self._DRDY, GPIO.IN)
        self.setup_adc(0, 1)

    def setup_adc(self, bus, device):
        self.spi.open(bus, device)

        # ADS131M09 Settings
        self.spi.mode = 0b01
        self.spi.max_speed_hz  = 1000000
        self.spi.no_cs = True  # We tied the ~CS to GND

    def read(self):
        if self._first_read:
            self.spi.writebytes([0b0] * self.num_frame_words * self.bytes_per_word)

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
 
        shifted_data_payload = [*(data << shift_value).to_bytes(self.bytes_per_word, 'big')]
        cmd = (WREG_OPCODE | register_addr << register_shift | len(shifted_data_payload)) << shift_value
        cmd_payload = [*cmd.to_bytes(self.bytes_per_word, 'big')]

        self.spi.writebytes(cmd_payload)
        self.spi.writebytes(shifted_data_payload)


if __name__ == '__main__':
    adc_reader = ADS131M09Reader()
    # currently using SPI1 pins
    # adc_reader.setup_adc(0, 1)

    # wait for DRDY to go high, indicating the ADC has started up
    while not GPIO.input(adc_reader._DRDY):
        print('not ready')
    print('ready')
    adc_reader.adc_register_write(CLOCK_ADDR, ALL_CH_DISABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK)
    adc_reader.adc_register_write(MODE_ADDR,  RESET_MASK | WLEN_24_MASK | SPI_TIMEOUT_MASK)
#    adc_reader.adc_register_write(GAIN1_ADDR, PGAGAIN3_32_MASK | PGAGAIN1_32_MASK)
#    adc_reader.adc_register_write(THRSHLD_LSB_ADDR, 0x09)
    adc_reader.adc_register_write(MODE_ADDR, WLENGTH_32_SIGN_EXTEND_MASK | DRDY_FMT_PULSE_MASK | SPI_TIMEOUT_MASK)
    adc_reader.adc_register_write(CLOCK_ADDR, ALL_CH_ENABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK)
    
    try:
        while True: pass
    except KeyboardInterrupt:
        pass

    


