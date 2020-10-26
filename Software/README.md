# ADC Driver


`gpclk_config/` - contains the `dt-blob.dts` file required to run the ADC. See the README for instructions on setting up the Raspberry Pi.

`adc_reader.py` - defines the `ADCReader` abstract base class, includes the basic operations for ADC drivers for this project

`ads131m08_reader.py` - defines the `ADS131M08Reader` driver for the ADS131M08. The `if __name__ == '__main__'` block at the bottom of the file has an example of running the software.

`consts.py` - defines specific constants for the `ADS131M08Reader` class, such as register addresses, commands, e.t.c.

`crc.py` - defines the CRC functions for communications with the ADC.

