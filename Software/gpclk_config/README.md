Clock configured by Device Tree Blob

- https://www.raspberrypi.org/documentation/configuration/pin-configuration.md
- https://www.tablix.org/~avian/blog/archives/2018/02/notes\_on\_the\_general\_purpose\_clocki\_on\_bcm2835/

TL;DR: We write the following section under `videocore` in `dt-blob.dts` (currently around lines 2260)
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

We compile the `dts` to `bin` and move it to the `/boot` folder with the following nifty command (see the [raspberry pi documentation](sudo dtc -I dts -O dtb -o /boot/dt-blob.bin dt-blob.dts) for installation and more information):

`sudo dtc -I dts -O dtb -o /boot/dt-blob.bin dt-blob.dts`

On reboot, the `dt-blob.bin` file should run and we should have a 1 MHz clock on `GPCLK0`, which translates to [GPIO 4, pin 7](https://pinout.xyz/pinout/gpclk).

