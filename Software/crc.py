""" Axel, 23 Sept. 2020
Found on stack overflow
https://stackoverflow.com/questions/25239423/crc-ccitt-16-bit-python-manual-calculation/64033322#64033322
which is a Python port from
https://www.lammertbies.nl/comm/info/crc-calculation

However, the Python port on Stackoverflow is incorrect. CRC-CCITT requires 16 bits of 0s leading
the message being checked, which the python port didn't include. The ADC also uses the incorrect
CRC-CCITT implementation, so that is what we will use.
See http://srecord.sourceforge.net/crc16-ccitt.html
"""

POLYNOMIAL = 0x1021
PRESET = 0xFFFF


def _initial(c):
    crc = 0
    c = c << 8
    for j in range(8):
        if (crc ^ c) & 0x8000:
            crc = (crc << 1) ^ POLYNOMIAL
        else:
            crc = crc << 1
        c = c << 1
    return crc


_tab = [ _initial(i) for i in range(256) ]


def _update_crc(crc, c):
    cc = 0xff & c

    tmp = (crc >> 8) ^ cc
    crc = (crc << 8) ^ _tab[tmp & 0xff]
    crc = crc & 0xffff

    return crc


def crcb(*i):
    crc = PRESET
    for c in i:
        crc = _update_crc(crc, c)
    return crc

