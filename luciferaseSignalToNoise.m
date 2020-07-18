% A back of envelope calculation to estimate how much signal we will get
% for the luminometer project, how that will compare to the detector
% noise floor, how much gain we will need, and whether we expect to be
% sensitive enough for the split luciferase assay.

% Paul Lebel, Diane Wiener
% 2020/07/14

clear;

% Physical constants
h = 6.6E-34;
c = 3E8;
lambda_m = 475E-9;
joulesPerPhoton = h*(c/lambda_m);
nAv = 6.02E23;
electronCharge = 1.6E-19;

% Our system, independent parameters
% Transimpedance gain, in Ohms
gain = 1E9; 
% Starting point
integrationTime_s = 100;
% Educated guess
collectionEfficiency = 0.3; 
% From OPT101 datasheet at 475 nm 
ampsPerWatt = 0.23; 
% (NEP) From OPT301 plot with 100M gain at 1 Hz, which seems like the same
% sensor but with an expanded range on the plots. NEP improves with higher
% gain - we might do better because we plan on using more gain than 100M
noiseEquivalentPower_W = 4E-13; 
% From OPT101 datasheet
darkCurrent_A = 2.5E-12;
% ADC bit depth 
bitDepth = 24; 
% ADC reference voltage
refVoltage = 5;

% Nanoluc is consistently reported as being 150x brighter than
% firefly, which I found a reference that reports 1.6/s with 40% QE. Units
% are photons/(enzyme second)
enzymePhotonRate = 1.6*0.41*150; 

% Reagents details fom Susanna, Jim Wells' lab. Relevant range is 1 pM to 1
% fM, but adding a decade on either side for comparison.
sampleVolume_L = 35E-6; 
enzymeConcentration_M = logspace(-11,-16, 30);

% Calculated values
Nenzymes = nAv*enzymeConcentration_M*sampleVolume_L;
photonsPerSecond = enzymePhotonRate*Nenzymes;
wattsEmitted = photonsPerSecond*joulesPerPhoton;
wattsCollected = collectionEfficiency*wattsEmitted;
photonsCollected = photonsPerSecond*integrationTime_s;
quantizationLowerLimit = refVoltage/(2^bitDepth);
voltageOut = wattsCollected*ampsPerWatt*gain;
noiseEquivalentPower_V = noiseEquivalentPower_W*ampsPerWatt*gain/sqrt(integrationTime_s);
photonShotNoise_V = sqrt(photonsCollected)*joulesPerPhoton*gain*ampsPerWatt/integrationTime_s;
darkElectrons = darkCurrent_A*integrationTime_s/electronCharge;
darkElectronsRMS = sqrt(darkElectrons);
darkVoltageRMS = darkElectronsRMS*electronCharge*gain/integrationTime_s;
sbr_nep = voltageOut./noiseEquivalentPower_V;
snr_phot = voltageOut./photonShotNoise_V;
snr_elec = voltageOut./darkVoltageRMS;
snr_tot = voltageOut./(sqrt(darkVoltageRMS^2 + photonShotNoise_V.^2));


% Plotting
figure('Position',[100,50, 600,700]);
% subplot(2,1,1);
% fill([1E-15,1E-12,1E-12,1E-15],[1E-8, 1E-8, 1E0,1E0],[.9,1,.9],'linestyle','none'); hold all; 
% set(gca, 'xscale','log');
% set(gca, 'yscale','log');
loglog(enzymeConcentration_M, voltageOut, '-','linewidth',2); hold all;
loglog(enzymeConcentration_M, quantizationLowerLimit*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, photonShotNoise_V, '-','linewidth',2);
loglog(enzymeConcentration_M, noiseEquivalentPower_V*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, darkVoltageRMS*ones(numel(enzymeConcentration_M),1), '-','linewidth',2);
loglog(enzymeConcentration_M, voltageOut./snr_tot, '-','linewidth',2); hold all;

grid;
ylabel('Voltage out','fontsize',16);
legend('Calculated signal',...
    'ADC lower limit',...
    'Photon Shot Noise',...
    'Noise Equivalent Power (NEP)',...
    'Dark current shot noise',...
    'Total shot noise',...
    'location','northwest');
title({'Nanoluc detection with OPT101 in high angle collection module',[num2str(integrationTime_s) ' s integration']})
xlabel('Enzyme concentration [M]','fontsize',16);

% subplot(2,1,2);
figure;
% fill([1E-15,1E-12,1E-12,1E-15],[1E0, 1E0, 1E8,1E8],[.9,1,.9],'linestyle','none'); hold all; 
% set(gca, 'xscale','log');
% set(gca, 'yscale','log');
loglog(enzymeConcentration_M, sbr_nep,'linewidth',2); hold all;
loglog(enzymeConcentration_M, snr_phot,'linewidth',2);
loglog(enzymeConcentration_M, snr_elec, 'linewidth',2); 
loglog(enzymeConcentration_M, snr_tot, 'linewidth',2); 

ylim([1E0,1E8]);
grid;
title('SNR metrics');
ylabel('SNR Metrics','fontsize',16);
xlabel('Enzyme concentration [M]','fontsize',16);
legend('Signal to NEP ratio',...
    'Signal to photon shot noise',...
    'Dark current shot noise',...
    'Total shot noise',...
    'location','northwest');

