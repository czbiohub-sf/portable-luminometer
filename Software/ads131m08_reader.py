#! /usr/bin/env python3
""" ADS131M08 Driver

-- Important Links --

ADC communication is via SPI - the Wikipedia article is worth a read
    https://en.wikipedia.org/wiki/Serial_Peripheral_Interface
If is one diagram to see, it is this one
    https://en.wikipedia.org/wiki/Serial_Peripheral_Interface#/media/File:SPI_8-bit_circular_transfer.svg
And Finally, here is the ADC datasheet
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
import spidev
import RPi.GPIO as GPIO

from typing import List

from crc import crcb
from adc_reader import ADCReader


# Set gpio pin numbering to the gpio pin numbers on the raspberry pi
GPIO.setmode(GPIO.BCM)


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


class CRCError(Exception):
    pass


class ADS131M08Reader(ADCReader):
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.ads_num_frame_words: int = 10  # Num. words in full ADS131 frame
        self.ads_bits_per_word: int = 24  # default word length on ADS
        self.rpi_bits_per_word: int = 8  # only available word length on RPi
        self.bytes_per_word: int = int(self.ads_bits_per_word / self.rpi_bits_per_word)  # 3 bytes per word

        self._DRDY: int = 21  # drdy pin is BCM 21

        # Flag for clearing ADC FIFO buffer; see Datasheet 8.5.1.9.1
        self._first_read: bool = True

        # Raspberry Pi GPIO inputs are all either pull-up or pull-down. Therefore, we must configure the
        # ADS131's DRDY pin to be an open-drain digital output, and the RPI's GPIO pin with the onboard
        # pull-up resistor; see Datasheet 8.5.1.5
        GPIO.setup(self._DRDY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def setup_adc(self, device: int, channels: List[int] = [2, 3]):
        """
        On the Raspberry Pi, SPI bus 0 supports SPI mode 1 and 3; The ADS131M08 communicates in SPI mode
        1. Therefore, the SPI bus must be bus 0.

        params:
            device: The device number for the ADC - will depend on the pinout of the ADC to RPi.
                    For the luminometer project, this will be device 1 (i.e. device = 1)
            channels: The list of channels to initalize. Each number must be between 0 and 7 inclusive (corresponding
                      to channels 0 to 7)
        """
        self.spi.open(0, device)

        # ADS131M08 Settings
        self.spi.mode = 0b01  # SPI Mode 1; See Datasheet 8.5.1
        self.spi.max_speed_hz = 488000  # 488 kHz clock speed
        self.spi.no_cs = False

        # Channel selection for the ADS131M08
        channel_enable_mask = 0b00000000
        for chl in channels:
            if chl > 7 or chl < 0:
                raise CRCError(
                    "Channels must be between 0 and 7 inclusive, corresponding to the channels on the ADC"
                )
            channel_enable_mask |= 0b1 << chl

        # Left shift the channel enable mask by 8 positions
        channel_enable_mask <<= 8

        # Initialize ADC to desired settings
        self.init_ads_config(channel_enable_mask)

    def init_ads_config(self, channel_enable_mask: int):
        """
        Sets the necessary settings for the ADS131M08, mostly hardcoded for the ulc-luminometer-project. See the datasheet
        for information about each of the settings.

        channel_enable_mask is the mask of channels to enable. It is a byte of values (1 if that channel is enabled, else 0),
        left-shifted by 8 positions.
        e.g. channel_enable_mask == 0b00001100 << 8 would enable channels 2 and 3
        """
        self.write_register(
            CLOCK_ADDR, ALL_CH_DISABLE_MASK | OSR_8192_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK,
        )
        self.write_register(
            MODE_ADDR, CLEAR_RESET_MASK | WLEN_24_MASK | SPI_TIMEOUT_MASK | DRDY_HIZ_OPEN_COLLECT | DRDY_FMT_PULSE_MASK,
        )
        self.write_register(CFG_ADDR, GLOBAL_CHOP_EN_MASK | DEFAULT_CHOP_DELAY_MASK)
        self.write_register(
            CLOCK_ADDR, channel_enable_mask | OSR_8192_MASK | PWR_HIGH_RES_MASK | XTAL_OSC_DISABLE_MASK,
        )

    def read_register(self, register_addr: int, num_registers: int = 1) -> List[float]:
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
        if not crc_check(ret_data):
            raise CRCError(f"CRC CHECK FAILED ON read_register({register_addr}, {num_registers})")
        return ret_data

    def read(self) -> List[float]:
        """
        Read all 8 ADC channels, and return the voltages in a list.
        
        For example, to read channels 0, 3, and 4, (let adc_reader be the initialized ADS131M08 object)
        data = adc_reader.read()
        ch0_voltage, ch3_voltage, ch4_voltage = data[0], data[3], data[4]
        """
        # the null command frame is used to read from the ADC
        null_cmd_frame = [0b0] * self.ads_num_frame_words * self.bytes_per_word

        # clear the FIFO buffer on first read; see Datasheet 8.5.1.9.1
        if self._first_read:
            self.spi.writebytes2(null_cmd_frame)
            self.spi.readbytes(len(null_cmd_frame))
            self._first_read = False

        self.spi.writebytes2(null_cmd_frame)
        res = self.spi.readbytes(len(null_cmd_frame))

        if not crc_check(res):
            raise CRCError(f"CRC CHECK FAILED ON read METHOD")

        # ADC data is returned in Two's Complement format; see Datasheet 8.5.1.9
        for i in range(1, 9):
            res[i] = twos_complement(res[i], 24)

        # Combine bytes back into words of bytes_per_word length before returning.
        data = [combine_bytes(*res[i : i + self.bytes_per_word]) for i in range(0, len(res), self.bytes_per_word)]
        adc_data = [self.adc_val_to_voltage(v) for v in data[1:9]]
        return adc_data

    def adc_val_to_voltage(self, adc_val: int) -> float:
        """
        Takes the adc value (which is an integer) and returns the corresponding voltage
        Reference: 8.5.1.9
        """
        if adc_val > 0x7FFFFF:
            adc_val -= 0xFFFFFF
        return 1.2 * adc_val / (2 ** 23)

    def write_register(self, register_addr: int, data: int) -> List[int]:
        """
        params
                register_addr:     16-bit register address mask
                data:              data to write

        Datasheet 8.5.1.10.8
        The ADS write command is 0b011a aaaa annn nnnn, where a aaaa a is the
        address of the register, and nnn nnnn is the number of consecutive registers
        to write to, minus 1.
        Therefore, we shift the register address left by 7
        """
        shift_value = self.ads_bits_per_word - 16
        register_addr_shift = 7

        # Shift the data (which is 16 bits) to three word requirement and then split the word into individual bytes
        data = data << shift_value
        shifted_data_payload = [*(data).to_bytes(self.bytes_per_word, "big")]

        # Format the WREG opcode according to the datasheet, and then split the word into individual bytes
        cmd = (
            WREG_OPCODE
            | (register_addr << register_addr_shift)
            | (int(len(shifted_data_payload) / self.bytes_per_word) - 1)
        ) << shift_value
        cmd_payload = [*cmd.to_bytes(self.bytes_per_word, "big")]

        total_payload = cmd_payload + shifted_data_payload
        cmd_frame = total_payload + [0] * self.bytes_per_word * (10 - int(len(total_payload) / self.bytes_per_word))

        self.spi.writebytes2(cmd_frame)
        ret_data = self.spi.readbytes(len(cmd_frame))

        if not crc_check(ret_data):
            raise CRCError(f"CRC CHECK FAILED ON write_register({register_addr}, {data})")
        return ret_data

    def write(self, cmd: int) -> List[int]:
        shift_value = self.ads_bits_per_word - 16
        shifted_cmd = [*(cmd << shift_value).to_bytes(self.bytes_per_word, "big")]
        cmd_frame = shifted_cmd + [0] * self.bytes_per_word * (10 - int(len(shifted_cmd) / self.bytes_per_word))

        self.spi.writebytes2(cmd_frame)
        time.sleep(10e-6)
        return self.spi.readbytes(len(cmd_frame))

    def data_ready(self) -> bool:
        """
        DRDY is active low, and pulses low when data is ready. 
        """
        return not GPIO.input(adc_reader._DRDY)


# Helper functions for manipulating bytes, performing CRC checks, e.t.c.
def bytes_to_readable(res, bytes_per_word=3) -> List[str]:
    return [bits(res[i : i + bytes_per_word]) for i in range(0, len(res), bytes_per_word)]


def crc_check(d: List[int]) -> bool:
    # The last 24-bit word of d is the 16-bit CRC, with 8 bits of 0 padding
    # on the LSB. The CRC is on the first 9 words of the communication frame
    return crcb(*d[:-3]) == combine_bytes(*d[-3:-1])


def combine_bytes(*byte_args: int) -> int:
    return int.from_bytes(byte_args, byteorder="big")


def bits(vs: List[int]) -> str:
    """
    vs is a list of bytes (i.e. integers in the range [0, 255])
    """
    bit_string = ""
    for v in vs:
        bs = "{0:b}".format(v)
        bit_string += "0" * (8 - len(bs)) + bs
    return " ".join([bit_string[i : i + 4] for i in range(0, len(bit_string), 4)])


def twos_complement(input_value: int, num_bits: int) -> int:
    """Calculates a two's complement integer from the given input value's bits."""
    mask = 2 ** (num_bits - 1)
    return -(input_value & mask) + (input_value & ~mask)


if __name__ == "__main__":
    device = 1  # using CE1
    adc_reader = ADS131M08Reader()
    adc_reader.setup_adc(device, channels=[2,3])

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
    def cb(channel):
        global sc, d1, d2
        sc += 1
        try:
            d = adc_reader.read()
        except CRCError:
            errs += 1
        d1 += d[2]
        d2 += d[3]
        print(d[2], d[3])

    GPIO.add_event_detect(adc_reader._DRDY, GPIO.FALLING, callback=cb)

    t0 = time.time()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        t1 = time.time()
        GPIO.cleanup()

    print(f"\n{sc} samples in {t1 - t0:.5} seconds. Sample rate of {sc / (t1 - t0)} Hz")
    print(f"CH2: = {d1 / sc} \t CH3 = {d2 / sc} \t CH2 - CH3 = {(d1 - d2) / sc}\n")
    print(f"{errs} CRC Errors encountered.")

