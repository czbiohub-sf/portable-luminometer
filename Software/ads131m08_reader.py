#! /usr/bin/env python3
"""
Application Notes:
    1. The ADS has can take a bits-per-word length of 16, 24, or 32.  Raspberry Pis are only configured tor 8 bits per word. Therefore, we
       just send each byte in every word individually.
    2. Reading data after a pause: see 8.5.1.9.1

The ADS131M08 performs all communication in SPI communication frames:

=====
8.5.1.7 SPI Communication Frames SPI communication on the ADS131M08 is performed in frames. Each SPI communication frame consists of several words.
The word size is configurable as either 16 bits, 24 bits, or 32 bits by programming the WLENGTH[1:0] bits in the MODE register.
-- NOTE FROM AXEL: We can configure this to what we want, but 24 bits seems to be the way to go. Since Raspberry Pi's are 8 bit,
-- we have to do a bit of manual work splitting and combining bites to send over SPI

The interface is full duplex, meaning that the interface is capable of transmitting data on DOUT while simultaneously receiving
data on DIN. The input frame that the host sends on DIN always begins with a command. The first word on the output frame that
the device transmits on DOUT always begins with the response to the command that was written on the previous input frame. The
number of words in a command depends on the command provided. For most commands, there are ten words in a frame. On DIN, the
host provides the command, the command CRC if input CRC is enabled or a word of zeros if input CRC is disabled, and eight
additional words of zeros.

Simultaneously on DOUT, the device outputs the response from the previous frame command, eight words of ADC data representing
the eight ADC channels, and a CRC word.

8.5.1.8 SPI Communication Words
The device defaults to a 24-bit word size. Commands, responses, CRC, and registers always contain 16 bits of actual data.
These words are always most significant bit (MSB) aligned, and therefore the least significant bits (LSBs) are zero-padded
to accommodate 24- or 32-bit word sizes.
=====
"""

import time
import spidev
import RPi.GPIO as GPIO

from typing import List

from crc import crcb
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
CFG_ADDR = 0x06
REGMAP_CRC_ADDR = 0x3E


# Register Payloads
# clock register
ALL_CH_DISABLE_MASK = 0b00000000 << 8
ALL_CH_ENABLE_MASK  = 0b11111111 << 8
CH_2_3_ENABLE_MASK  = 0b00001100 << 8
OSR_16256_MASK = 0b111 << 2
# The datasheet is a bit confusing with regards to the chrystal oscillator.
# For the luminometer design, we give the ADC the SCLK from the master SPI.
# Therefore, we enable the XTAL_OSC_DISABLE bit of the clock register
# I found this a bit unclear, see the link from the chip developer below
# https://e2e.ti.com/support/data-converters/f/73/t/905809
XTAL_OSC_DISABLE_MASK = 0b1 << 7
EXTERNAL_REF_MASK = 0b0 << 6
PWR_HIGH_RES_MASK = 0b11

# mode register
REG_CRC_EN_MASK = 0b1 << 13
CRC_IN_EN_MASK = 0b1 << 12
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


class ADS131M09Reader(ADCReader):
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.ads_num_frame_words: int = 10  # Num. words in full ADS131 frame
        self.ads_bits_per_word: int = 24  # default word length on ADS
        self.rpi_bits_per_word: int = 8  # only available word length on RPi
        self.bytes_per_word: int = int(self.ads_bits_per_word / self.rpi_bits_per_word)

        self._DRDY: int = 11  # drdy pin is 37
        self._first_read: bool = False

        GPIO.setup(self._DRDY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def setup_adc(self, bus, device):
        self.spi.open(bus, device)

        # ADS131M09 Settings
        self.spi.mode = 0b01
        self.spi.max_speed_hz = int(1e6)
        self.spi.no_cs = True  # We tied the ~CS to GND

    def read(self):
        if self._first_read:
            self.spi.writebytes2([0b0] * self.ads_num_frame_words * self.bytes_per_word)
            self._first_read = True
        cmd_frame = [0b0] * self.ads_num_frame_words * self.bytes_per_word
        self.spi.writebytes2(cmd_frame)
        res = self.spi.readbytes(len(cmd_frame))

        res = self.spi.readbytes(len(cmd_frame)) 
        if not self.crc_check(res):
            print(f'CRC CHECK FAILED ON read()')

        # Combine the bytes back into words before returning
        for i in range(1, 10):
            res[i] = twos_complement(res[i], 24)
        data = [combine_bytes(*res[i:i + self.bytes_per_word]) for i in range(0, len(res), self.bytes_per_word)]
        return data

    def write_register(self, register_addr: int, data: int):
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

        data = data << shift_value
        shifted_data_payload = [*(data).to_bytes(self.bytes_per_word, "big")]

        cmd = (WREG_OPCODE | (register_addr << register_shift) | (int(len(shifted_data_payload) / self.bytes_per_word) - 1)) << shift_value
        cmd_payload = [*cmd.to_bytes(self.bytes_per_word, "big")]

        total_payload = cmd_payload + shifted_data_payload
        cmd_frame = total_payload + [0] * self.bytes_per_word * (10 - int(len(total_payload) / self.bytes_per_word))
        self.spi.writebytes2(cmd_frame)

        print(f'write_register: {register_addr}', self.bytes_to_readable(total_payload))
        ret_data = self.spi.readbytes(len(cmd_frame)) 
        if not self.crc_check(ret_data):
            print(f'CRC CHECK FAILED ON write_register({register_addr}, {data})')
        return ret_data

    def write(self, cmd):
        shift_value = self.ads_bits_per_word - 16
        shifted_cmd = [*(cmd << shift_value).to_bytes(self.bytes_per_word, "big")]
        cmd_frame = shifted_cmd + [0] * self.bytes_per_word * (10 - int(len(shifted_cmd) / self.bytes_per_word))

        self.spi.writebytes2(cmd_frame)
        time.sleep(10e-6)
        return self.spi.readbytes(len(cmd_frame))

    def read_register(self, register_addr: int, num_registers: int = 1):
        """
        params
                register_addr:     16-bit register address mask
                num_registers:     number of consecutive registers to read

        Read from register given at the register address
        """
        if num_registers < 1:
            return

        shift_value = self.ads_bits_per_word - 16
        register_shift = 7

        cmd = (RREG_OPCODE | (register_addr << register_shift) | (num_registers - 1)) << shift_value
        cmd_payload = [*cmd.to_bytes(self.bytes_per_word, "big")]
        cmd_frame = cmd_payload + [0] * self.bytes_per_word * (10 - int(len(cmd_payload) / self.bytes_per_word))
        self.spi.writebytes2(cmd_frame)

        # if one register is being read, the expected frame back is 10 words long
        # else, it is the number of requested registers, plus the confimation, plus the crc.
        # hence, 2 + num_registers words are expected back
        if num_registers == 1:
            bytes_to_read = self.bytes_per_word * 10
        else:
            bytes_to_read = self.bytes_per_word * (2 + num_registers)

        ret_data = self.spi.readbytes(bytes_to_read)
        if not self.crc_check(ret_data):
            print(f'CRC CHECK FAILED ON read_register({register_addr}, {num_registers})')
        return ret_data

    def data_ready(self):
        return not GPIO.input(adc_reader._DRDY)

    def bytes_to_readable(self, res):
        return [bits(res[i:i + self.bytes_per_word]) for i in range(0, len(res), self.bytes_per_word)]

    def crc_check(self, d: List[int]) -> bool:
        # The last 24-bit word of d is the 16-bit CRC, with 8 bits of 0 padding
        # on the LSB. The CRC is on the first 9 words of the communication frame
        return crcb(*d[:-3]) == combine_bytes(*d[-3:-1])

def combine_bytes(*byte_args):
    return int.from_bytes(byte_args, byteorder='big')

def bits(vs: List[int]):
    """
    vs is a list of bytes (i.e. integers in the range [0, 255])
    """
    bit_string = ''
    for v in vs:
        bs = '{0:b}'.format(v)
        bit_string += '0' * (8 - len(bs)) + bs 
    return ' '.join([bit_string[i:i+4] for i in range(0, len(bit_string), 4)])

def twos_complement(input_value: int, num_bits: int) -> int:
    """Calculates a two's complement integer from the given input value's bits."""
    mask = 2 ** (num_bits - 1)
    return -(input_value & mask) + (input_value & ~mask)


if __name__ == "__main__":
    adc_reader = ADS131M09Reader()
    adc_reader.setup_adc(0, 1)

    # wait for DRDY to go high, indicating the ADC has started up
    while not GPIO.input(adc_reader._DRDY):
        print("not ready")
    print("ready")

    adc_reader.write_register(CLOCK_ADDR, ALL_CH_DISABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK)
    adc_reader.write_register(MODE_ADDR, CLEAR_RESET_MASK |  WLEN_24_MASK | SPI_TIMEOUT_MASK | DRDY_HIZ_OPEN_COLLECT) # DRDY_FMT_PULSE_MASK |
    adc_reader.write_register(CFG_ADDR, GLOBAL_CHOP_EN_MASK | DEFAULT_CHOP_DELAY_MASK)
    adc_reader.write_register(CLOCK_ADDR, CH_2_3_ENABLE_MASK | OSR_16256_MASK | PWR_HIGH_RES_MASK| XTAL_OSC_DISABLE_MASK)

    print('ID')
    d = adc_reader.read_register(ID_ADDR)
    print(adc_reader.bytes_to_readable(d)[0])
    print()

    print('MODE')
    d = adc_reader.read_register(MODE_ADDR)
    print(adc_reader.bytes_to_readable(d)[0])
    print()

    print('CLOCK')
    d = adc_reader.read_register(CLOCK_ADDR)
    print(adc_reader.bytes_to_readable(d)[0])
    print()

    print('CFG')
    d = adc_reader.read_register(CFG_ADDR)
    print(adc_reader.bytes_to_readable(d)[0])
    print()

    print('STATUS register')
    d = adc_reader.read_register(STATUS_ADDR)
    print(adc_reader.bytes_to_readable(d)[0])
    print()

    while True:
        data = adc_reader.read()
        print(1.2 * data[3] / (2**23), 1.2 * data[4] / (2**23))

