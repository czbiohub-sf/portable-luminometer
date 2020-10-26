# Clock configured by Device Tree Blob

## Pi Setup

We compile the `dts` to `bin` and move it to the `/boot` folder with the following nifty command (see the [raspberry pi documentation](https://www.raspberrypi.org/documentation/configuration/pin-configuration.md) for installation and more information):

`sudo dtc -I dts -O dtb -o /boot/dt-blob.bin dt-blob.dts`

On reboot, the `dt-blob.bin` file should run and we should have a 1 MHz clock on `GPCLK0`, which translates to [GPIO 4, pin 7](https://pinout.xyz/pinout/gpclk).

## Explanation / Sources

- https://www.raspberrypi.org/documentation/configuration/pin-configuration.md
- https://www.tablix.org/~avian/blog/archives/2018/02/notes_on_the_general_purpose_clock_on_bcm2835/

TL;DR: We write the following section under `videocore` in `dt-blob.dts`
```
clock_routing {
  vco@PLLA { freq = <1920000000>; };
     chan@APER { div = <4>; };
     clock@GPCLK0 { pll = "PLLA"; chan = "APER"; };
};
clock_setup {
  clock@GPCLK0 { freq = <1000000>; };
};
```
