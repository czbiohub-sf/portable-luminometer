# Release notes

All notable changes to this project will be documented in this file. This module adheres to [Semantic Versioning](https://semver.org/).
<!-- 
Given a version number MAJOR.MINOR.PATCH, increment the:

MAJOR version when you make incompatible API changes,
MINOR version when you add functionality in a backwards compatible manner, and
PATCH version when you make backwards compatible bug fixes.
Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.
 -->

## 0.0.1
Initial commit after preliminary development.

## 1.0.0
A number of changes have been implemented since the initial commit. A [user guide](https://tinyurl.com/3p8p7axm) has been created that goes over (at a high-level) the key functionality that is part of this update.

### New menu navigation system
- For a more detailed walkthrough of the menu system (with accompanying images), see the user guide.
- Manual exposure: measurements now display the number of samples taken so far (x/TOTAL). Previously the time elapsed (X(s)/TOTAL(s)) was displayed. See the shutter/ADC coupling change under 'Other miscellaneous changes' for details on why this change was made.
- Repeat measurement: users can now repeat the current measurement once it has been completed by pressing the middle button from the final measurement screen.
- A status/diagnostic menu screen has been added which displays battery status, 34V in range, SiPM Bias in range, number of CRC errors (which occurred during the most recent measurement), and HBridge errors. Additionally the scaled ADC outputs (sensor A, sensor B, SiPMRef, SiPMBias, and 34V) can be viewed as well.
- The ability to perform and save a custom temperature calibration alongside an immutable factory default calibration has been added. A user can toggle between the two calibrations through the calibration menu. Note that the expected usage is for a user to calibrate the device and always use their custom calibration. The factory default is provided as a fallback in the event of debugging/error.
- `RLU_PER_V` normalization calibration: functionality has been added to normalize measurements to a `TARGET_RLU` (with an offset, `ADD_OFFSET_RLU`, to ensure only nonnegative values are displayed). These variables are located in `luminometer_constants.py` (and are currently set to 1000 and 10 respectively). The normalization constants are stored in a newly created file `RLU.json`. This normalization is intended to only be done at the point of assembly and not by the user. This normalization is hidden away in a secret menu which can be accessed by entering the status/diagnostic menu screen and pressing the following buttons: TOP-MIDDLE-TOP-MIDDLE (and allowing a brief pause between button presses to ensure the presses register). If this combination does not work, it is likely that a button bounced or was not registered - simply re-enter the status menu and try again.
- During initial assembly, there were two types of InkyPHAT screens that were used (`InkyPHAT` and `InkyPHAT_SSD1608`), each requiring a slightly different initialization. As such, a `screen_type.json` file was used to specify which screen to initialize on each device by calling the correct screen constructor. The screen types were arbitrarily labelled '1' and '2', respectively.
- Autoexposure - **note - no changes, but a reminder**: Currently there is no way to specify which of the tube holder channels should be used when performing an autoexposure. Future functionality will add the ability to pick either one or both channels on which to run an autoexposure measurement.

### Other miscellaneous changes
- Change to button callback structure: there is now one unified button callback which manages the logic of what action to take.
- A flag has been added, `screen_settled`, to ensure that screen/state transitions only occur once the screen has fully settled. This does lead to an annoying delay between when it appears like the screen has finished displaying and when a button press will actually be registered. This delay is currently around 2s (in addition to the ~5s it takes the screen to update). This is a limitation of how quickly the e-ink screens will update. We did test running the menu system without the flag, however the display and state would quickly come out of sync leading to user confusion. Additionally occasionlly, when screen transitions are triggered during the middle of a previous transition, it was found that the screen sometimes froze halfway through the update.
- Logging with a rotating file handler has been added, stored in `luminometer-logs/luminometer.log`. The current logfile size is set to 5MB with 3 backup files kept when the filesize is reached.
- Devicetree - added in line to prevent low-battery on start-up
User guide has been created
- An `all-measurements.csv` file has been added which records all the measurements taken on a device with the following headers: (`date`, `measurementMode`, `exposure`, `resultA`, `standard_err_of_mean_A`, `resultB`, `standard_err_of_mean_B`)
- The latest SD card `.img` has been saved to the [Google Drive](https://drive.google.com/drive/folders/1eKodaykWZre6_c7QN1SxxQCyukg3vkI2?usp=sharing) (note that a `git pull` is still necessary to update the repository to the latest changes)
- `pigpio` is now used instead of `RPi.GPIO` to run the motor PWM (`RPi.GPIO` uses software PWM with significant jitter)
- The ADC and shutter use separate `pigpio.pi()` objects (each object has its own callback thread). The button presses still use `RPi.GPIO`. Note that since `RPi.GPIO` only has a single callback thread, previously if a button was pressed or held during a measurement, this would interrupt the shutter swings and ADC data collection. 
- Shutter swings and ADC data collection are now coupled. Previously the `SKIP_SAMPLES` parameter was set to 3, which meant that the first and last 3 data points taken during a sample (i.e an open/close period) were discarded. This was done to account for datapoints that were taken during the middle of shutter swings (despite there being a wait time to account for the shutter acutation time, since the operating system is not an RTOS, this delay could not be relied upon). By coupling the ADC and shutter swings (i.e data points are only collected once the shutters are fully held open/closed and they set a flag to assert as such), data points need not be tossed out. 
    - Additionally, because the timing of the shutter open/close is not reliably consistent (because Raspabian is not an RTOS), a fixed "expected measurement runtime" can not be displayed. This is why the number of samples is now displayed instead.
- Python's built-in `time.sleep()` function was replaced with a `better_sleep()` function which busy waits and provides better timing (however in hindsight this is likely an undesirable change that should be reverted. Busy waiting provides microsecond accuracy as compared with Python's `sleep()`'s millisecond accuracy, however this level of timing granularity is not necessary for our application. Additionally busy_waiting expends far more resources than `sleep()`'s simple thread suspension).
- `dt-blob.dts` has an added line to PULL_UP on pin21 to prevent the low battery LED from falsely turning on during startup.
- Several additional constants have been added to `luminometer_constants.py`
- `config.txt`: Uncommented the line setting the chip select pin to pin 4. On Raspberry Pi OS 5.10.17+, having this line in the file caused the GPCLK to go high during the boot sequence.