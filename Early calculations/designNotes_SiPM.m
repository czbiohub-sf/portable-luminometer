
% Design journal for the Ultra-Low-Cost Luminometer for detecting nanoluc
% luciferase.

% SiPM version
% Using OnSemi part number: MICROFC?60035?SMT 
% 6x6 mm silicon photomultipler chip

% Paul Lebel
% 2020/09/01

% Physical constants
ambientTemp_C = 20;
h = 6.6E-34;
c = 3E8;
lambda_m = 460E-9;
joulesPerPhoton = h*(c/lambda_m);
nAv = 6.02E23;
electronCharge = 1.6E-19;

% Independent parameters of our system
% Transimpedance gain, in Ohms
transimpedanceGain = 2E5; 

integrationTime_s = 1;

% This is a reasonable guess, given that the enzyme photon rate was
% adjusted to match experimental measurement using 0.3 and the OPT101. The
% SiPM is 4x larger and will collect at least 2x more light. 
collectionEfficiency = 2*0.3; 

% From MICROFC?60035?SMT datasheet at 2.5 V over voltage 
ampsPerWatt = 1E6;
pmtGain = 3E6;

% Dark current data from sensor datasheet at 2.5 V over voltage (figure 8)
tempData_C = [-20,0,20,40,60];
darkCurrentData_A = [32, 100, 618, 3200, 30000]*1E-9;
darkCurrentAmbient_typical = interp1(tempData_C, darkCurrentData_A, ambientTemp_C,'PCHIP');

% From datasheet - max spec is 3x typical value
darkCurrent_A_max = 3*darkCurrentAmbient_typical;

% ADC bit depth 
bitDepth = 24; 
% ADC max voltage input range
adcRange = 2.4;

% Nanoluc is consistently reported as being 150x brighter than
% firefly, which I found a reference that reports 1.6/s with 40% QE. Units
% are photons/(enzyme second). 
% Update: this number is being divided by 750 due to experimental
% measurement of enzyme in the lab, on an OPT101 chip.
enzymePhotonRate = 1.6*0.41*150/750; 

% Reagents details fom Susanna, Jim Wells' lab. Relevant range is 1 pM to 1
% fM, but adding a decade on either side for comparison.
sampleVolume_L = 35E-6; 
enzymeConcentration_M = logspace(-11,-16, 30);

% Calculated values
Nenzymes = nAv*enzymeConcentration_M*sampleVolume_L;
photonsPerSecond = enzymePhotonRate*Nenzymes;
wattsEmitted = photonsPerSecond*joulesPerPhoton;
wattsCollected = collectionEfficiency*wattsEmitted;
photonsCollected = collectionEfficiency*photonsPerSecond*integrationTime_s;
quantizationLowerLimit = adcRange/(2^bitDepth);
voltageOut = wattsCollected*ampsPerWatt*transimpedanceGain;
photoCurrent_A = wattsCollected*ampsPerWatt;

% Photon shot noise
photonShotNoise_V = sqrt(photonsCollected)*joulesPerPhoton*transimpedanceGain*ampsPerWatt/integrationTime_s;

% Dark current mean and standard deviation (shot noise == RMS)
darkElectrons = darkCurrentAmbient_typical*integrationTime_s/electronCharge;
darkElectrons_max = darkCurrent_A_max*integrationTime_s/electronCharge;
darkElectronsRMS = pmtGain*sqrt(darkElectrons/pmtGain);
darkElectronsRMS_max = pmtGain*sqrt(darkElectrons_max/pmtGain);

% Convert to voltages
darkVoltageOffset = darkCurrentAmbient_typical*transimpedanceGain;
darkVoltageOffset_max = darkCurrent_A_max*transimpedanceGain;
darkVoltageRMS = darkElectronsRMS*electronCharge*transimpedanceGain/integrationTime_s;
darkVoltageRMS_max = darkElectronsRMS_max*electronCharge*transimpedanceGain/integrationTime_s;
totalNoiseRMS = sqrt(darkVoltageRMS.^2 + photonShotNoise_V.^2);

% Plot signal levels
figure('Position',[100,50, 750,700]);
loglog(enzymeConcentration_M, voltageOut, 'k-','linewidth',2); hold all;
loglog(enzymeConcentration_M, photonShotNoise_V, '-.','linewidth',2);
loglog(enzymeConcentration_M, darkVoltageOffset*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, darkVoltageOffset_max*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, darkVoltageRMS*ones(numel(enzymeConcentration_M),1), '-.','linewidth',2);
loglog(enzymeConcentration_M, darkVoltageRMS_max*ones(numel(enzymeConcentration_M),1), '-.','linewidth',2);
loglog(enzymeConcentration_M, quantizationLowerLimit*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, adcRange*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
set(gca,'fontsize',16);
grid;
axis tight;
xlim([min(enzymeConcentration_M), max(enzymeConcentration_M)]);
ylim([1E-8, 4]);
ylabel('Voltage out','fontsize',16);
legend('Calculated signal',...
    'Photon Shot Noise',...
    'Dark current offset - Typical',...
    'Dark current offset - MAX',...
    'Dark current shot noise - Typical',...
    'Dark current shot noise - MAX',...
    'ADC lower limit',...,
    'ADC saturation upper limit',...
    'location','NorthWest', 'fontsize',14);
title({['Nanoluc detection with SiPM at ', num2str(ambientTemp_C), '\circC'],[num2str(integrationTime_s) ' s integration']}, 'fontsize',16)
xlabel('Enzyme concentration [M]','fontsize',16);

