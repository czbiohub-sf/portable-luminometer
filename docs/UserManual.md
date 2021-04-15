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
<img src = "https://user-images.githubusercontent.com/30475643/114794262-ee839280-9d40-11eb-962d-150d2e095a7a.png" width="340">
The luminometer uses high-sensitivity Silicon Photomultiplier (SiPM) sensors to detect low levels of light. SiPM sensors consist of arrays of internal Avalanche Photodiodes (APDs) with extremely high internal gain, resulting in a large signal amplification for each photon that is detected. The drawback of such sensors is their dark current -- that is, signal that appears regardless of the amount of light hitting the sensor-- which is very strongly dependent on temperature. In practice, this means that all measurements we make consist of the actual luminescence signal added on top of a time-varying dark signal that drifts with the temperature of the sensors. Without mitigation, the drift of the dark signal would dwarf the signals we are trying to measure.

To compensate for the dark signal drift, a swinging shutter arm was introduced. The shutter repeatedly blocks and unblocks the light from hitting the sensor, allowing us to perform repeated dark offset measurements over time, as we accumulate enough signal from the sample. Each period of time the shutter is either open or closed, a series of data samples are acquired and averaged, giving us a sequence of datapoints corresponding to alternating open and closed periods. To subtract the dark offset, each shutter open datapoint is subtracted by the mean of its flanking closed periods. Using both flanking closed periods fully compensates for linear drift in the dark signal. To achieve this, every measurement is programmed to start and end with shutter-closed periods.

For example, if the total measurement time is set to 7 seconds and the shutter period is 1 second, then there will be 3 shutter-open periods and 4 shutter-closed periods: _-_-_-_. 

After the subtraction is completed, the signal is now gated and the averaged datapoints can themselves be averaged together to produce a single number, and because our final answer is the result of averaging multiple independent samples, the standard error of the mean can be reported as a statistical measure of the uncertainty due to counting statistics of dark current shot noise. 

Finally, there is a residual shutter-induced voltage offset corresponding to a difference in gated signal that occurs even in the absence of a sample or background light. This residual offset must be calibrated 

## Operation Guide

### Powering up and shutting down
__Important!__
- Only plug and unplug the charging cable while the power switch is off.
- Only turn the power switch off after the device has powered down (see bottom button, below), and you have waited 15 seconds after the screen displays the message 'Powering down...'

__Powering up__
Simply flip the power switch on and wait for the screen to display its ready message. This may take approximately 60 seconds. 

__Shutting down__ 
- At any time, hold the bottom button for at least three seconds, until a 'beep' is heard. 
- The screen will display a 'Powering down...' message. 
- Wait 15 seconds after the message is displayed
- Turn the power switch to 'Off'.

### Making measurements
After power up, the instrument waits for button pushes in a ready state.

#### Top button
__During the READY state__
Starts a measurement using the auto-exposure feature. The device will continue measureing for a minimum of 7 seconds, or until one of the following conditions is met:
- The Signal-To-Noise (SNR) has exceeded the target value (a hard-coded value). SNR is defined as the mean of all the gated shutter-open samples divided by the standard error of the mean of the same datapoints. The SNR improves over time, as the counting statistics improve with more integrated signal.
- The exposure duration has exceeded a hard-coded maximum (3,000 seconds)

__During a measurement__
Holding the top button down for three seconds will halt any measurement (auto, fixed, or dark), display the final result, and return to the READY state.

#### Middle button
__During the READY state__
The middle button is configured for the user to select a fixed manual exposure time, from a list of possibilities, depending on the duration the button is held. 
- A brief click sets exposure to 10s
- Holding for 1 second sets exposure to 30 s(the instrument will beep once to confirm). 
- Holding for 2 seconds sets exposure to 30 s(the instrument will beep again to confirm). 
- Holding for 3 seconds sets exposure to 60 s(the instrument will beep again to confirm). 
- Holding for 4 seconds sets exposure to 300 s(the instrument will beep again to confirm). 
- Holding for 5 seconds sets exposure to 600 s(the instrument will beep again to confirm). 

#### Bottom button
__During the READY state__
The bottom button starts a dark reference measurement. By default, the exposure goes indefinitely until aborted. The dark reference can therefore be acquired for as long as required in order to improve precision, as displayed over time on the screen. 

Holding bottom button for three seconds (not during measurement) powers down the device.

### Mechanical Details

### Electrical Details

### Software Details

### Validation Results
