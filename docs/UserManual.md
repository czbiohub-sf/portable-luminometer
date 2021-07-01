# User Guide

## Contents
- Theory of Operation
- Operation Guide
  - Powering up and shutting down
  - Making measurements
- Mechanical Details
- Electrical Details
- Software Details
- Validation Results

## Theory of Operation
<img src = "https://github.com/czbiohub/ulc-tube-reader/blob/software-v1.2-changes/docs/luminometer_complete.png" width="400">

The luminometer uses high-sensitivity Silicon Photomultiplier (SiPM) sensors to detect low levels of light. SiPM sensors consist of arrays of internal Avalanche Photodiodes (APDs) with extremely high internal gain, resulting in a large signal amplification for each photon that is detected. The drawback of such sensors is their dark current -- that is, signal that appears regardless of the amount of light hitting the sensor-- which is very strongly dependent on temperature. In practice, this means that all measurements we make consist of the actual luminescence signal added on top of a time-varying dark signal that drifts with the temperature of the sensors. Without mitigation, the drift of the dark signal would dwarf the signals we are trying to measure.

To compensate for the dark signal drift, a swinging shutter arm was introduced. The shutter repeatedly blocks and unblocks the light from hitting the sensor, allowing us to perform repeated dark offset measurements over time, as we accumulate enough light from the sample. Each period of time the shutter is either open or closed, a series of data samples are acquired and averaged, giving us a sequence of datapoints corresponding to alternating open and closed periods. To subtract the dark offset, each shutter open datapoint is subtracted by the mean of its flanking closed periods. Using both flanking closed periods fully compensates for linear drift in the dark signal. To achieve this, every measurement is programmed to start and end with shutter-closed periods.

For example, if the total measurement time is set to 9 seconds and the shutter period is 1 second, then there will be 4 shutter-open periods and 5 shutter-closed periods: \_\-\_\-\_\-\_\-\_. 

After the subtraction is completed, the signal is now gated and the averaged datapoints can themselves be averaged together to produce a single number, and because our final answer is the result of averaging multiple independent samples, the standard error of the mean can be reported as a statistical measure of the uncertainty due to counting statistics of dark current shot noise. 

Finally, there is a residual signal offset corresponding to a difference in signal between shutter-open and shutter-closed states, even in the absence of a sample. This residual offset is thought to be caused by emission and subsequent detection of light from and by the sensor itself. We have developed an automated calibration routine that corrects for this effect and is applied to all incoming measurements. By measuring both the raw dark current and the shutter offset error over a range of temperatures, we can create a linear fit capable of predicting the residual shutter offset as a function of raw dark current. Experimental measurements can therefore by fully-compensated for temperature drift, by virtue of shutter gating and temperature compensation.

## Operation Guide

### Powering up and shutting down
__Important!__
- Always wait 15 seconds after the luminometer software has been shut down before turning the main power switch off.

__Powering up__
Flip the power switch on the side panel to the up position and wait for the screen to display its ready message. This will take 30-60 seconds. 

__Powering down__ 
- At any time, hold the bottom button until three 'beeps' are heard.
- The screen will display a 'POWER OFF' message. 
- Wait 15 seconds after this message is displayed
- Turn the power switch to the down position.

### Making measurements
- During measurements, always keep the device laying still, and flat its back during measurements (screen facing upwards). Do not bump or disturb the device during measurements.
- When inserting a PCR tube, always ensure it is pushed all the way down into the tube holder, such that the brim firmly contacts top surface of the tube holder.
- Always use the exact recommended model of PCR tube. Changes to the make/model of PCR tube may alter the accuracy and/or precision of measurements due to differences in shape/size of the tube, which alter the optics of the measurement cavity. If absolutely necessary to change tubes, it is necessary to repeat the thermal compensation calibration. Never use tinted or colored tubes.
- Making measurements:
  1. Upon power up, the instrument sits in a ready state, waiting for button pushes.
  2. Insert sample(s) into the tube holder, and fully close both the tube holder and the access lids.
  3. Lay the box flat on its back with the screen facing the ceiling. Do not bump or disturb the box during measurements. 
  4. To start a measurement, either click the top button once (auto-exposure) or press and hold the middle button (fixed exposure). See detailed descriptions for each button below.
  5. During a measurement, the screen will update the user with a current estimate of the result based on the data accumulated thus far. The screen indicates whether the measurement is still ongoing (Final: No) or whether the measurement has completed (Final: Yes). During the measurement, the shutter can be heard clicking open and closed. If the shutter clicking is not heard, then the shutter is malfunctioning and the data will not be usable.
  6. At any time, a measurement can be halted by holding the top button for three seconds.
  7. When the measurement has completed on its own, the device will beep to announce completion, and the shutter will stop clicking. Once the final measurement is available, the result will be displayed on the screen with "Final: Yes".
  8. It is the operator's responsibility to record all measurements from the result displayed on the screen. Although an internal measurement log is kept on board the device, it is not accessible to the user via the button/screen interface.

#### Top button
__During the READY state__
Starts a measurement using the auto-exposure feature. The device will continue measuring (the minimum is 7 seconds), until the Signal-To-Noise (SNR) has exceeded the hard-coded target value. SNR is defined as the mean of all the gated shutter-open samples divided by the standard error of the mean of the same datapoints. The SNR improves over time, as the counting statistics improve with more accumulated signal.

__During a measurement__
Holding the top button down for three seconds will halt any measurement (auto, fixed, or calibration), display the final result, and return to the READY state.

#### Middle button
__During the READY state__
The middle button is configured for the user to select a fixed manual exposure time, from a list of possibilities, depending on the duration the button is held. 
- A brief click sets exposure to 10s
- Holding for 1 second sets exposure to 30 s(the instrument will beep once to confirm). 
- Holding for 2 seconds sets exposure to 30 s(the instrument will beep again to confirm). 
- Holding for 3 seconds sets exposure to 60 s(the instrument will beep again to confirm). 
- Holding for 4 seconds sets exposure to 300 s(the instrument will beep again to confirm). 
- Holding for 5 seconds sets exposure to 600 s(the instrument will beep again to confirm). 

__During a measurement__
No action taken

#### Bottom button
__During the READY state__
- The bottom button is mainly used for switching the power off: holding bottom button for three seconds powers down the device. Remember to always wait at least 15 seconds after the 'POWER OFF' message is displayed before turning the physical power switch off.
- Calibration mode: 

### Battery charging
The device uses a mini-USB interface for charging. The 4400 mA-hr

### Mechanical Details

### Electrical Details

### Software Details

### Validation Results
