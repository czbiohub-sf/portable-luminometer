EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title "Luminometer ADC"
Date "2020-08-06"
Rev "A"
Comp "Chan Zuckerberg Biohub"
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L ADS131M08:ADS131M08IPBS U2
U 1 1 5F205E39
P 7275 1725
F 0 "U2" H 7250 1914 60  0000 C CNN
F 1 "ADS131M08IPBS" H 7250 1808 60  0000 C CNN
F 2 "Package_QFP:LQFP-32_5x5mm_P0.5mm" H 7275 -775 60  0001 C CNN
F 3 "https://www.ti.com/lit/ds/symlink/ads131m08.pdf?ts=1595957796694&ref_url=https%253A%252F%252Fwww.ti.com%252Fproduct%252FADS131M08" H 7250 1808 60  0001 C CNN
	1    7275 1725
	1    0    0    -1  
$EndComp
$Comp
L Device:Resonator_Small Y1
U 1 1 5F208D3E
P 8325 1725
F 0 "Y1" V 8650 1675 50  0000 C CNN
F 1 "CSTNE8M19" V 8559 1675 50  0000 C CNN
F 2 "Crystal:Resonator_SMD_muRata_CSTxExxV-3Pin_3.0x1.1mm" H 8300 1725 50  0001 C CNN
F 3 "https://www.murata.com/products/productdata/8801159970846/SPEC-CSTNE8M00GH5L000R0.pdf" H 8300 1725 50  0001 C CNN
	1    8325 1725
	0    -1   -1   0   
$EndComp
$Comp
L Device:R R1
U 1 1 5F20AEC9
P 6025 1775
F 0 "R1" V 6075 1625 50  0000 C CNN
F 1 "470" V 6025 1775 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 5955 1775 50  0001 C CNN
F 3 "~" H 6025 1775 50  0001 C CNN
	1    6025 1775
	0    1    1    0   
$EndComp
$Comp
L Device:C_Small C3
U 1 1 5F20BF9B
P 6225 1875
F 0 "C3" H 6325 1875 50  0000 L CNN
F 1 "1uF" H 5925 1875 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 6225 1875 50  0001 C CNN
F 3 "~" H 6225 1875 50  0001 C CNN
	1    6225 1875
	1    0    0    -1  
$EndComp
Wire Wire Line
	6425 1825 6325 1825
Wire Wire Line
	6325 1825 6325 1775
Wire Wire Line
	6325 1775 6225 1775
Wire Wire Line
	6425 1925 6325 1925
Wire Wire Line
	6325 1925 6325 1975
Wire Wire Line
	6325 1975 6225 1975
Wire Wire Line
	6225 1775 6175 1775
Connection ~ 6225 1775
Wire Wire Line
	6175 1975 6225 1975
Connection ~ 6225 1975
Wire Wire Line
	6425 2125 6325 2125
Wire Wire Line
	6325 2125 6325 2075
Wire Wire Line
	6425 2225 6325 2225
Wire Wire Line
	6325 2225 6325 2275
Wire Wire Line
	5875 1775 5525 1775
Text Label 5525 1975 0    50   ~ 0
ADC0P
Text Label 5525 1775 0    50   ~ 0
ADC0N
Wire Wire Line
	5875 1975 5525 1975
Wire Wire Line
	5875 2075 5525 2075
Text Label 5525 2275 0    50   ~ 0
ADC1P
Text Label 5525 2075 0    50   ~ 0
ADC1N
Wire Wire Line
	5875 2275 5525 2275
Wire Wire Line
	8075 1925 8225 1925
Wire Wire Line
	8225 1925 8225 1825
Wire Wire Line
	8225 1625 8075 1625
Wire Wire Line
	8075 1625 8075 1825
$Comp
L Device:R R3
U 1 1 5F22E58F
P 8325 2025
F 0 "R3" V 8275 2175 50  0000 C CNN
F 1 "470" V 8325 2025 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 8255 2025 50  0001 C CNN
F 3 "~" H 8325 2025 50  0001 C CNN
	1    8325 2025
	0    1    1    0   
$EndComp
Wire Wire Line
	8175 2025 8075 2025
NoConn ~ 8075 2125
Wire Wire Line
	8475 2025 8575 2025
Wire Wire Line
	8575 2025 8575 1975
$Comp
L power:+3V3 #PWR08
U 1 1 5F237BBA
P 8575 1975
F 0 "#PWR08" H 8575 1825 50  0001 C CNN
F 1 "+3V3" H 8590 2148 50  0000 C CNN
F 2 "" H 8575 1975 50  0001 C CNN
F 3 "" H 8575 1975 50  0001 C CNN
	1    8575 1975
	1    0    0    -1  
$EndComp
Wire Wire Line
	8525 1725 8775 1725
Wire Wire Line
	8775 1725 8775 2225
$Comp
L Device:C_Small C5
U 1 1 5F240BCB
P 8325 2225
F 0 "C5" V 8275 2325 50  0000 C CNN
F 1 "220nF" V 8375 2425 50  0000 C CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 8325 2225 50  0001 C CNN
F 3 "~" H 8325 2225 50  0001 C CNN
	1    8325 2225
	0    1    1    0   
$EndComp
Wire Wire Line
	8075 2225 8225 2225
Wire Wire Line
	8425 2225 8775 2225
Wire Wire Line
	8775 2225 8775 2275
Connection ~ 8775 2225
$Comp
L power:GNDD #PWR015
U 1 1 5F24D8B6
P 8775 2275
F 0 "#PWR015" H 8775 2025 50  0001 C CNN
F 1 "GNDD" H 8779 2120 50  0000 C CNN
F 2 "" H 8775 2275 50  0001 C CNN
F 3 "" H 8775 2275 50  0001 C CNN
	1    8775 2275
	1    0    0    -1  
$EndComp
Wire Wire Line
	8075 2525 8375 2525
$Comp
L Device:R R2
U 1 1 5F25839E
P 6025 1975
F 0 "R2" V 5975 1825 50  0000 C CNN
F 1 "470" V 6025 1975 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 5955 1975 50  0001 C CNN
F 3 "~" H 6025 1975 50  0001 C CNN
	1    6025 1975
	0    1    1    0   
$EndComp
Wire Wire Line
	8075 2425 8525 2425
Wire Wire Line
	8525 2425 8525 2475
Wire Wire Line
	8075 2625 8375 2625
Wire Wire Line
	8075 2725 8375 2725
Text Label 8375 2725 2    50   ~ 0
MOSI
Text Label 8375 2625 2    50   ~ 0
MISO
Text Label 8375 2525 2    50   ~ 0
SCLK
Text Label 8375 2425 2    50   ~ 0
~CS
Wire Wire Line
	8525 2675 8525 2725
$Comp
L power:GNDD #PWR021
U 1 1 5F29FF7C
P 8525 2725
F 0 "#PWR021" H 8525 2475 50  0001 C CNN
F 1 "GNDD" H 8529 2570 50  0000 C CNN
F 2 "" H 8525 2725 50  0001 C CNN
F 3 "" H 8525 2725 50  0001 C CNN
	1    8525 2725
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C11
U 1 1 5F2A0D2E
P 8275 3325
F 0 "C11" H 8367 3371 50  0000 L CNN
F 1 "220nF" H 8367 3280 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 8275 3325 50  0001 C CNN
F 3 "~" H 8275 3325 50  0001 C CNN
	1    8275 3325
	1    0    0    -1  
$EndComp
Wire Wire Line
	8075 3325 8175 3325
Wire Wire Line
	8175 3325 8175 3425
Wire Wire Line
	8175 3425 8075 3425
Wire Wire Line
	8175 3425 8275 3425
Connection ~ 8175 3425
Wire Wire Line
	8275 3225 8075 3225
Wire Wire Line
	8075 3125 8775 3125
$Comp
L Device:C_Small C12
U 1 1 5F2AFA7A
P 8775 3325
F 0 "C12" H 8867 3371 50  0000 L CNN
F 1 "1uF" H 8867 3280 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 8775 3325 50  0001 C CNN
F 3 "~" H 8775 3325 50  0001 C CNN
	1    8775 3325
	1    0    0    -1  
$EndComp
Wire Wire Line
	8275 3425 8775 3425
Connection ~ 8275 3425
Wire Wire Line
	8775 3225 8775 3125
$Comp
L power:GNDA #PWR027
U 1 1 5F2B80B2
P 8775 3475
F 0 "#PWR027" H 8775 3225 50  0001 C CNN
F 1 "GNDA" H 8780 3302 50  0000 C CNN
F 2 "" H 8775 3475 50  0001 C CNN
F 3 "" H 8775 3475 50  0001 C CNN
	1    8775 3475
	1    0    0    -1  
$EndComp
Wire Wire Line
	8775 3475 8775 3425
Connection ~ 8775 3425
$Comp
L power:+3V0 #PWR026
U 1 1 5F2BC20F
P 8775 3125
F 0 "#PWR026" H 8775 2975 50  0001 C CNN
F 1 "+3V0" H 8790 3298 50  0000 C CNN
F 2 "" H 8775 3125 50  0001 C CNN
F 3 "" H 8775 3125 50  0001 C CNN
	1    8775 3125
	1    0    0    -1  
$EndComp
Connection ~ 8775 3125
$Comp
L Device:C_Small C15
U 1 1 5F2BD078
P 8225 3825
F 0 "C15" H 8317 3871 50  0000 L CNN
F 1 "1uF" H 8317 3780 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 8225 3825 50  0001 C CNN
F 3 "~" H 8225 3825 50  0001 C CNN
	1    8225 3825
	1    0    0    -1  
$EndComp
Wire Wire Line
	8075 3775 8075 3725
Wire Wire Line
	8075 3725 8225 3725
Wire Wire Line
	8075 3875 8075 3925
Wire Wire Line
	8075 3925 8225 3925
Wire Wire Line
	8225 3925 8225 3975
Connection ~ 8225 3925
$Comp
L power:GNDD #PWR032
U 1 1 5F2C90A7
P 8225 3975
F 0 "#PWR032" H 8225 3725 50  0001 C CNN
F 1 "GNDD" H 8229 3820 50  0000 C CNN
F 2 "" H 8225 3975 50  0001 C CNN
F 3 "" H 8225 3975 50  0001 C CNN
	1    8225 3975
	1    0    0    -1  
$EndComp
Wire Wire Line
	8225 3725 8225 3675
Connection ~ 8225 3725
$Comp
L power:+3V3 #PWR030
U 1 1 5F2CD7CF
P 8225 3675
F 0 "#PWR030" H 8225 3525 50  0001 C CNN
F 1 "+3V3" H 8240 3848 50  0000 C CNN
F 2 "" H 8225 3675 50  0001 C CNN
F 3 "" H 8225 3675 50  0001 C CNN
	1    8225 3675
	1    0    0    -1  
$EndComp
Wire Wire Line
	8275 3225 8525 3225
Connection ~ 8275 3225
Text Label 8525 3225 2    50   ~ 0
REF
$Comp
L Reference_Voltage:CJ432 U4
U 1 1 5F30ECC5
P 1250 7075
F 0 "U4" V 1296 7005 50  0000 R CNN
F 1 "ADR512" V 1205 7005 50  0000 R CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 1250 6925 50  0001 C CIN
F 3 "https://www.analog.com/media/en/technical-documentation/data-sheets/ADR512.pdf" H 1250 7075 50  0001 C CIN
	1    1250 7075
	0    -1   -1   0   
$EndComp
Wire Wire Line
	1250 7175 1250 7225
$Comp
L power:GNDA #PWR033
U 1 1 5F316F03
P 1250 7325
F 0 "#PWR033" H 1250 7075 50  0001 C CNN
F 1 "GNDA" H 1255 7152 50  0000 C CNN
F 2 "" H 1250 7325 50  0001 C CNN
F 3 "" H 1250 7325 50  0001 C CNN
	1    1250 7325
	1    0    0    -1  
$EndComp
Wire Wire Line
	1250 6975 1250 6925
Wire Wire Line
	1250 6925 1700 6925
Wire Wire Line
	1250 6925 1250 6825
Connection ~ 1250 6925
$Comp
L Device:R R16
U 1 1 5F32F48A
P 1250 6675
F 0 "R16" H 1320 6721 50  0000 L CNN
F 1 "470" V 1250 6625 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 1180 6675 50  0001 C CNN
F 3 "~" H 1250 6675 50  0001 C CNN
	1    1250 6675
	1    0    0    -1  
$EndComp
Wire Wire Line
	1250 6525 1250 6475
NoConn ~ 1150 7075
Text Label 2000 6925 2    50   ~ 0
REF
$Comp
L Regulator_Linear:LP5907MFX-3.0 U1
U 1 1 5F3A9B1A
P 4925 6825
F 0 "U1" H 4925 7192 50  0000 C CNN
F 1 "LP5907MFX-4.5" H 4925 7101 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23-5" H 4925 7175 50  0001 C CNN
F 3 "http://www.ti.com/lit/ds/symlink/lp5907.pdf" H 4925 7325 50  0001 C CNN
	1    4925 6825
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C2
U 1 1 5F3AB957
P 5325 6925
F 0 "C2" H 5417 6971 50  0000 L CNN
F 1 "1uF" H 5417 6880 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 5325 6925 50  0001 C CNN
F 3 "~" H 5325 6925 50  0001 C CNN
	1    5325 6925
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C1
U 1 1 5F3AC695
P 4475 6925
F 0 "C1" H 4567 6971 50  0000 L CNN
F 1 "1uF" H 4567 6880 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 4475 6925 50  0001 C CNN
F 3 "~" H 4475 6925 50  0001 C CNN
	1    4475 6925
	1    0    0    -1  
$EndComp
Wire Wire Line
	4475 6825 4475 6725
Wire Wire Line
	4475 6725 4575 6725
Wire Wire Line
	4625 6825 4575 6825
Wire Wire Line
	4575 6825 4575 6725
Connection ~ 4575 6725
Wire Wire Line
	4575 6725 4625 6725
Wire Wire Line
	4475 7025 4475 7225
Wire Wire Line
	4475 7225 4925 7225
Wire Wire Line
	5325 7225 5325 7025
Wire Wire Line
	5325 6825 5325 6725
Wire Wire Line
	5325 6725 5225 6725
Wire Wire Line
	4925 7125 4925 7225
Connection ~ 4925 7225
Wire Wire Line
	4925 7225 5325 7225
Wire Wire Line
	4925 7225 4925 7275
$Comp
L power:GNDA #PWR03
U 1 1 5F401864
P 4925 7275
F 0 "#PWR03" H 4925 7025 50  0001 C CNN
F 1 "GNDA" H 4930 7102 50  0000 C CNN
F 2 "" H 4925 7275 50  0001 C CNN
F 3 "" H 4925 7275 50  0001 C CNN
	1    4925 7275
	1    0    0    -1  
$EndComp
Wire Wire Line
	4475 6725 4475 6675
Connection ~ 4475 6725
Wire Wire Line
	5325 6725 5325 6675
Connection ~ 5325 6725
$Comp
L Connector_Generic:Conn_01x08 J9
U 1 1 5F46DBC4
P 10350 3400
F 0 "J9" H 10430 3392 50  0000 L CNN
F 1 "Conn_01x08" H 10430 3301 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical" H 10350 3400 50  0001 C CNN
F 3 "~" H 10350 3400 50  0001 C CNN
	1    10350 3400
	1    0    0    -1  
$EndComp
Wire Wire Line
	10150 3400 9950 3400
Wire Wire Line
	10150 3300 9950 3300
Wire Wire Line
	10150 3500 9950 3500
Wire Wire Line
	10150 3600 9950 3600
Text Label 9950 3600 0    50   ~ 0
MOSI
Text Label 9950 3500 0    50   ~ 0
MISO
Text Label 9950 3400 0    50   ~ 0
SCLK
Text Label 9950 3300 0    50   ~ 0
~CS
Wire Wire Line
	10150 3200 9950 3200
Wire Wire Line
	9950 3200 9950 3150
Wire Wire Line
	10150 3800 9950 3800
Wire Wire Line
	9950 3800 9950 3850
$Comp
L power:+3V3 #PWR031
U 1 1 5F4AB654
P 9950 3150
F 0 "#PWR031" H 9950 3000 50  0001 C CNN
F 1 "+3V3" H 9965 3323 50  0000 C CNN
F 2 "" H 9950 3150 50  0001 C CNN
F 3 "" H 9950 3150 50  0001 C CNN
	1    9950 3150
	1    0    0    -1  
$EndComp
$Comp
L power:GNDD #PWR034
U 1 1 5F4F745F
P 9950 3850
F 0 "#PWR034" H 9950 3600 50  0001 C CNN
F 1 "GNDD" H 9954 3695 50  0000 C CNN
F 2 "" H 9950 3850 50  0001 C CNN
F 3 "" H 9950 3850 50  0001 C CNN
	1    9950 3850
	1    0    0    -1  
$EndComp
$Comp
L Device:Jumper_NC_Small JP1
U 1 1 5F7DC857
P 8525 2575
F 0 "JP1" V 8525 2650 50  0000 L CNN
F 1 "Jumper_NC_Small" V 8570 2649 50  0001 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical" H 8525 2575 50  0001 C CNN
F 3 "~" H 8525 2575 50  0001 C CNN
	1    8525 2575
	0    1    1    0   
$EndComp
Text Notes 1050 1075 0    100  ~ 20
Silicon Photomultipliers
Text Notes 6875 1225 0    100  ~ 20
24b ADC
Text Notes 9600 1850 0    100  ~ 20
MCU Interface
Text Notes 4175 6275 0    100  ~ 20
Analog 4.5V Source
Text Notes 950  6175 0    100  ~ 20
1.2V 7mA REF
$Comp
L power:VDDA #PWR029
U 1 1 5F2E67DA
P 1250 6475
F 0 "#PWR029" H 1250 6325 50  0001 C CNN
F 1 "VDDA" H 1267 6648 50  0000 C CNN
F 2 "" H 1250 6475 50  0001 C CNN
F 3 "" H 1250 6475 50  0001 C CNN
	1    1250 6475
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR01
U 1 1 5F2F8B1B
P 4475 6675
F 0 "#PWR01" H 4475 6525 50  0001 C CNN
F 1 "+5V" H 4490 6848 50  0000 C CNN
F 2 "" H 4475 6675 50  0001 C CNN
F 3 "" H 4475 6675 50  0001 C CNN
	1    4475 6675
	1    0    0    -1  
$EndComp
$Comp
L power:VDDA #PWR02
U 1 1 5F3097AB
P 5325 6675
F 0 "#PWR02" H 5325 6525 50  0001 C CNN
F 1 "VDDA" H 5342 6848 50  0000 C CNN
F 2 "" H 5325 6675 50  0001 C CNN
F 3 "" H 5325 6675 50  0001 C CNN
	1    5325 6675
	1    0    0    -1  
$EndComp
Wire Wire Line
	10150 3100 10150 2950
$Comp
L power:+5V #PWR028
U 1 1 5F33A07E
P 10150 2900
F 0 "#PWR028" H 10150 2750 50  0001 C CNN
F 1 "+5V" H 10165 3073 50  0000 C CNN
F 2 "" H 10150 2900 50  0001 C CNN
F 3 "" H 10150 2900 50  0001 C CNN
	1    10150 2900
	1    0    0    -1  
$EndComp
Text Notes 7000 6800 0    50   ~ 0
Notes:\n1. Analog ground and digital ground must be joined at the ADC and nowhere else. Layout on page 95.\n2. Digital output value range for the ADC is detailed on page 33.
Wire Wire Line
	8775 3425 8975 3425
Wire Wire Line
	8975 3925 8225 3925
Wire Wire Line
	10150 3700 9950 3700
Wire Wire Line
	9950 3700 9950 3800
Connection ~ 9950 3800
$Comp
L Jumper:SolderJumper_2_Bridged JP2
U 1 1 5F3E929F
P 8975 3675
F 0 "JP2" V 8975 3743 50  0000 L CNN
F 1 "Bridge" V 9020 3743 50  0001 L CNN
F 2 "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm" H 8975 3675 50  0001 C CNN
F 3 "~" H 8975 3675 50  0001 C CNN
	1    8975 3675
	0    1    1    0   
$EndComp
Wire Wire Line
	8975 3825 8975 3925
Wire Wire Line
	8975 3525 8975 3425
$Comp
L Regulator_Linear:LP5907MFX-3.0 U3
U 1 1 5F439AC4
P 3250 6825
F 0 "U3" H 3250 7192 50  0000 C CNN
F 1 "LP5907MFX-3" H 3250 7101 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23-5" H 3250 7175 50  0001 C CNN
F 3 "http://www.ti.com/lit/ds/symlink/lp5907.pdf" H 3250 7325 50  0001 C CNN
	1    3250 6825
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C7
U 1 1 5F439ACA
P 3650 6925
F 0 "C7" H 3742 6971 50  0000 L CNN
F 1 "1uF" H 3742 6880 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 3650 6925 50  0001 C CNN
F 3 "~" H 3650 6925 50  0001 C CNN
	1    3650 6925
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C6
U 1 1 5F439AD0
P 2800 6925
F 0 "C6" H 2892 6971 50  0000 L CNN
F 1 "1uF" H 2892 6880 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 2800 6925 50  0001 C CNN
F 3 "~" H 2800 6925 50  0001 C CNN
	1    2800 6925
	1    0    0    -1  
$EndComp
Wire Wire Line
	2800 6825 2800 6725
Wire Wire Line
	2800 6725 2900 6725
Wire Wire Line
	2950 6825 2900 6825
Wire Wire Line
	2900 6825 2900 6725
Connection ~ 2900 6725
Wire Wire Line
	2900 6725 2950 6725
Wire Wire Line
	2800 7025 2800 7225
Wire Wire Line
	2800 7225 3250 7225
Wire Wire Line
	3650 7225 3650 7025
Wire Wire Line
	3650 6825 3650 6725
Wire Wire Line
	3650 6725 3550 6725
Wire Wire Line
	3250 7125 3250 7225
Connection ~ 3250 7225
Wire Wire Line
	3250 7225 3650 7225
Wire Wire Line
	3250 7225 3250 7275
$Comp
L power:GNDA #PWR020
U 1 1 5F439AE5
P 3250 7275
F 0 "#PWR020" H 3250 7025 50  0001 C CNN
F 1 "GNDA" H 3255 7102 50  0000 C CNN
F 2 "" H 3250 7275 50  0001 C CNN
F 3 "" H 3250 7275 50  0001 C CNN
	1    3250 7275
	1    0    0    -1  
$EndComp
Wire Wire Line
	2800 6725 2800 6675
Connection ~ 2800 6725
Wire Wire Line
	3650 6725 3650 6675
Connection ~ 3650 6725
$Comp
L power:+5V #PWR013
U 1 1 5F439AEF
P 2800 6675
F 0 "#PWR013" H 2800 6525 50  0001 C CNN
F 1 "+5V" H 2815 6848 50  0000 C CNN
F 2 "" H 2800 6675 50  0001 C CNN
F 3 "" H 2800 6675 50  0001 C CNN
	1    2800 6675
	1    0    0    -1  
$EndComp
$Comp
L power:+3V0 #PWR014
U 1 1 5F45CB94
P 3650 6675
F 0 "#PWR014" H 3650 6525 50  0001 C CNN
F 1 "+3V0" H 3665 6848 50  0000 C CNN
F 2 "" H 3650 6675 50  0001 C CNN
F 3 "" H 3650 6675 50  0001 C CNN
	1    3650 6675
	1    0    0    -1  
$EndComp
Text Notes 2600 6275 0    100  ~ 20
Analog 3V Source
$Comp
L Device:R R4
U 1 1 5F482985
P 6025 2075
F 0 "R4" V 6075 1925 50  0000 C CNN
F 1 "470" V 6025 2075 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 5955 2075 50  0001 C CNN
F 3 "~" H 6025 2075 50  0001 C CNN
	1    6025 2075
	0    1    1    0   
$EndComp
$Comp
L Device:C_Small C4
U 1 1 5F48298B
P 6225 2175
F 0 "C4" H 6325 2175 50  0000 L CNN
F 1 "1uF" H 5925 2175 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 6225 2175 50  0001 C CNN
F 3 "~" H 6225 2175 50  0001 C CNN
	1    6225 2175
	1    0    0    -1  
$EndComp
Wire Wire Line
	6325 2075 6225 2075
Wire Wire Line
	6325 2275 6225 2275
Wire Wire Line
	6225 2075 6175 2075
Connection ~ 6225 2075
Wire Wire Line
	6175 2275 6225 2275
Connection ~ 6225 2275
$Comp
L Device:R R5
U 1 1 5F482997
P 6025 2275
F 0 "R5" V 5975 2125 50  0000 C CNN
F 1 "470" V 6025 2275 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 5955 2275 50  0001 C CNN
F 3 "~" H 6025 2275 50  0001 C CNN
	1    6025 2275
	0    1    1    0   
$EndComp
$Comp
L Device:C_Small C17
U 1 1 5F2D8E12
P 1700 7075
F 0 "C17" H 1792 7121 50  0000 L CNN
F 1 "220nF" H 1792 7030 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1700 7075 50  0001 C CNN
F 3 "~" H 1700 7075 50  0001 C CNN
	1    1700 7075
	1    0    0    -1  
$EndComp
Wire Wire Line
	1700 6975 1700 6925
Connection ~ 1700 6925
Wire Wire Line
	1700 6925 2000 6925
Wire Wire Line
	1250 7225 1700 7225
Wire Wire Line
	1700 7225 1700 7175
Connection ~ 1250 7225
Wire Wire Line
	1250 7225 1250 7325
$Comp
L power:PWR_FLAG #FLG0101
U 1 1 5F64EEDA
P 10150 2950
F 0 "#FLG0101" H 10150 3025 50  0001 C CNN
F 1 "PWR_FLAG" V 10150 3078 50  0001 L CNN
F 2 "" H 10150 2950 50  0001 C CNN
F 3 "~" H 10150 2950 50  0001 C CNN
	1    10150 2950
	0    1    1    0   
$EndComp
Connection ~ 10150 2950
Wire Wire Line
	10150 2950 10150 2900
$Comp
L power:PWR_FLAG #FLG0102
U 1 1 5F64F31E
P 9950 3200
F 0 "#FLG0102" H 9950 3275 50  0001 C CNN
F 1 "PWR_FLAG" V 9950 3327 50  0001 L CNN
F 2 "" H 9950 3200 50  0001 C CNN
F 3 "~" H 9950 3200 50  0001 C CNN
	1    9950 3200
	0    -1   -1   0   
$EndComp
Connection ~ 9950 3200
$Comp
L power:PWR_FLAG #FLG0103
U 1 1 5F64FD3F
P 9950 3800
F 0 "#FLG0103" H 9950 3875 50  0001 C CNN
F 1 "PWR_FLAG" V 9950 3927 50  0001 L CNN
F 2 "" H 9950 3800 50  0001 C CNN
F 3 "~" H 9950 3800 50  0001 C CNN
	1    9950 3800
	0    -1   -1   0   
$EndComp
$Comp
L power:PWR_FLAG #FLG0104
U 1 1 5F65080C
P 8975 3425
F 0 "#FLG0104" H 8975 3500 50  0001 C CNN
F 1 "PWR_FLAG" V 8975 3552 50  0001 L CNN
F 2 "" H 8975 3425 50  0001 C CNN
F 3 "~" H 8975 3425 50  0001 C CNN
	1    8975 3425
	0    1    1    0   
$EndComp
Connection ~ 8975 3425
$Comp
L Mechanical:MountingHole_Pad H1
U 1 1 5F30D92E
P 9150 5625
F 0 "H1" H 9250 5628 50  0000 L CNN
F 1 "MountingHole_Pad" H 9250 5583 50  0001 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3_Pad" H 9150 5625 50  0001 C CNN
F 3 "~" H 9150 5625 50  0001 C CNN
	1    9150 5625
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole_Pad H2
U 1 1 5F30DD18
P 9500 5625
F 0 "H2" H 9600 5628 50  0000 L CNN
F 1 "MountingHole_Pad" H 9600 5583 50  0001 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3_Pad" H 9500 5625 50  0001 C CNN
F 3 "~" H 9500 5625 50  0001 C CNN
	1    9500 5625
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole_Pad H3
U 1 1 5F30E0C1
P 9800 5625
F 0 "H3" H 9900 5628 50  0000 L CNN
F 1 "MountingHole_Pad" H 9900 5583 50  0001 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3_Pad" H 9800 5625 50  0001 C CNN
F 3 "~" H 9800 5625 50  0001 C CNN
	1    9800 5625
	1    0    0    -1  
$EndComp
Wire Wire Line
	9800 5725 9800 5825
Wire Wire Line
	9800 5825 9650 5825
Wire Wire Line
	9150 5825 9150 5725
Wire Wire Line
	9500 5725 9500 5825
Connection ~ 9500 5825
Wire Wire Line
	9500 5825 9150 5825
Wire Wire Line
	9650 5825 9650 5975
$Comp
L power:GNDA #PWR0101
U 1 1 5F347488
P 9650 5975
F 0 "#PWR0101" H 9650 5725 50  0001 C CNN
F 1 "GNDA" H 9655 5802 50  0000 C CNN
F 2 "" H 9650 5975 50  0001 C CNN
F 3 "" H 9650 5975 50  0001 C CNN
	1    9650 5975
	1    0    0    -1  
$EndComp
$Comp
L Mechanical:MountingHole_Pad H4
U 1 1 5F35A8C5
P 10100 5625
F 0 "H4" H 10200 5628 50  0000 L CNN
F 1 "MountingHole_Pad" H 10200 5583 50  0001 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3_Pad" H 10100 5625 50  0001 C CNN
F 3 "~" H 10100 5625 50  0001 C CNN
	1    10100 5625
	1    0    0    -1  
$EndComp
Wire Wire Line
	9800 5825 10100 5825
Wire Wire Line
	10100 5825 10100 5725
Connection ~ 9800 5825
Connection ~ 9650 5825
Wire Wire Line
	9650 5825 9500 5825
$Comp
L LuminometerCustomPartLib:MICROFC−60035−SMT SiPM?
U 1 1 5F4B68CC
P 1175 1925
F 0 "SiPM?" H 1025 1900 39  0000 R CNN
F 1 "MICROFC−60035−SMT" H 1025 1800 39  0000 R CNN
F 2 "Luminometer_OPT101_Footprints:OnSemi_CASE512" H 1175 1375 39  0001 C CNN
F 3 "https://www.onsemi.com/pub/Collateral/MICROC-SERIES-D.PDF" H 1175 1925 100 0001 C CNN
	1    1175 1925
	-1   0    0    -1  
$EndComp
$Comp
L LuminometerCustomPartLib:OPA862 U?
U 1 1 5F4B8026
P 2350 2450
F 0 "U?" H 2450 2865 50  0000 C CNN
F 1 "OPA862" H 2450 2774 50  0000 C CNN
F 2 "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" H 2350 2800 50  0001 C CNN
F 3 "https://www.ti.com/lit/ds/symlink/opa862.pdf?HQS=TI-null-null-digikeymode-df-pf-null-wwe&ts=1596238612437" H 2350 2800 50  0001 C CNN
	1    2350 2450
	1    0    0    -1  
$EndComp
NoConn ~ 925  1925
$Comp
L Device:C_Small C?
U 1 1 5F4EBA72
P 1675 2675
F 0 "C?" H 1550 2600 50  0000 L CNN
F 1 "220uF" H 1425 2750 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1675 2675 50  0001 C CNN
F 3 "~" H 1675 2675 50  0001 C CNN
	1    1675 2675
	-1   0    0    -1  
$EndComp
$Comp
L power:GNDA #PWR?
U 1 1 5F4ED377
P 1675 2825
F 0 "#PWR?" H 1675 2575 50  0001 C CNN
F 1 "GNDA" H 1680 2652 50  0000 C CNN
F 2 "" H 1675 2825 50  0001 C CNN
F 3 "" H 1675 2825 50  0001 C CNN
	1    1675 2825
	-1   0    0    -1  
$EndComp
Text Label 2050 2400 2    50   ~ 0
REF
Wire Wire Line
	2850 2600 2850 3100
Wire Wire Line
	2125 3100 2050 3100
Text Label 2125 3100 0    50   ~ 0
ADC0P
Text Label 2750 3100 2    50   ~ 0
ADC0N
Wire Wire Line
	2850 3100 2750 3100
$Comp
L Device:R R?
U 1 1 5F65E9B0
P 1300 2600
F 0 "R?" H 1375 2750 50  0000 C CNN
F 1 "10k" V 1300 2600 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 1230 2600 50  0001 C CNN
F 3 "~" H 1300 2600 50  0001 C CNN
	1    1300 2600
	-1   0    0    1   
$EndComp
$Comp
L Device:C_Small C?
U 1 1 5F6936C0
P 1075 2600
F 0 "C?" H 1175 2650 50  0000 L CNN
F 1 "10uF" H 1175 2575 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1075 2600 50  0001 C CNN
F 3 "~" H 1075 2600 50  0001 C CNN
	1    1075 2600
	-1   0    0    -1  
$EndComp
Wire Wire Line
	2050 2300 1175 2300
Wire Wire Line
	1175 2300 1175 2425
Wire Wire Line
	1175 2425 1075 2425
Wire Wire Line
	1300 2425 1300 2450
Wire Wire Line
	1075 2500 1075 2425
Wire Wire Line
	1075 2700 1075 2850
Wire Wire Line
	1300 2850 1300 2750
Wire Wire Line
	1175 2175 1175 2300
Connection ~ 1175 2300
Connection ~ 1175 2425
Wire Wire Line
	1175 2425 1300 2425
$Comp
L power:GNDA #PWR?
U 1 1 5F817AD9
P 3075 2625
F 0 "#PWR?" H 3075 2375 50  0001 C CNN
F 1 "GNDA" H 3080 2452 50  0000 C CNN
F 2 "" H 3075 2625 50  0001 C CNN
F 3 "" H 3075 2625 50  0001 C CNN
	1    3075 2625
	-1   0    0    -1  
$EndComp
Wire Wire Line
	2850 2500 2950 2500
Wire Wire Line
	2850 2400 2950 2400
Wire Wire Line
	2950 2400 2950 2500
$Comp
L power:+3V0 #PWR?
U 1 1 5F8315C3
P 3075 2025
F 0 "#PWR?" H 3075 1875 50  0001 C CNN
F 1 "+3V0" H 3090 2198 50  0000 C CNN
F 2 "" H 3075 2025 50  0001 C CNN
F 3 "" H 3075 2025 50  0001 C CNN
	1    3075 2025
	1    0    0    -1  
$EndComp
Wire Wire Line
	2950 2300 2850 2300
$Comp
L power:VDDA #PWR?
U 1 1 5F83F7FB
P 1675 2450
F 0 "#PWR?" H 1675 2300 50  0001 C CNN
F 1 "VDDA" H 1525 2525 50  0000 C CNN
F 2 "" H 1675 2450 50  0001 C CNN
F 3 "" H 1675 2450 50  0001 C CNN
	1    1675 2450
	1    0    0    -1  
$EndComp
Wire Wire Line
	1675 2450 1675 2500
Wire Wire Line
	2050 2500 1675 2500
Wire Wire Line
	1675 2575 1675 2500
Connection ~ 1675 2500
Wire Wire Line
	1675 2775 1675 2825
Text Label 1175 1500 1    50   ~ 0
VBias
Wire Wire Line
	1175 1500 1175 1675
$Comp
L LuminometerCustomPartLib:MICROFC−60035−SMT SiPM?
U 1 1 5FB92A04
P 1150 4000
F 0 "SiPM?" H 1000 3975 39  0000 R CNN
F 1 "MICROFC−60035−SMT" H 1000 3875 39  0000 R CNN
F 2 "Luminometer_OPT101_Footprints:OnSemi_CASE512" H 1150 3450 39  0001 C CNN
F 3 "https://www.onsemi.com/pub/Collateral/MICROC-SERIES-D.PDF" H 1150 4000 100 0001 C CNN
	1    1150 4000
	-1   0    0    -1  
$EndComp
$Comp
L LuminometerCustomPartLib:OPA862 U?
U 1 1 5FB92A0A
P 2325 4525
F 0 "U?" H 2425 4940 50  0000 C CNN
F 1 "OPA862" H 2425 4849 50  0000 C CNN
F 2 "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" H 2325 4875 50  0001 C CNN
F 3 "https://www.ti.com/lit/ds/symlink/opa862.pdf?HQS=TI-null-null-digikeymode-df-pf-null-wwe&ts=1596238612437" H 2325 4875 50  0001 C CNN
	1    2325 4525
	1    0    0    -1  
$EndComp
NoConn ~ 900  4000
$Comp
L Device:C_Small C?
U 1 1 5FB92A11
P 1650 4750
F 0 "C?" H 1525 4675 50  0000 L CNN
F 1 "220uF" H 1400 4825 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1650 4750 50  0001 C CNN
F 3 "~" H 1650 4750 50  0001 C CNN
	1    1650 4750
	-1   0    0    -1  
$EndComp
$Comp
L power:GNDA #PWR?
U 1 1 5FB92A17
P 1650 4925
F 0 "#PWR?" H 1650 4675 50  0001 C CNN
F 1 "GNDA" H 1655 4752 50  0000 C CNN
F 2 "" H 1650 4925 50  0001 C CNN
F 3 "" H 1650 4925 50  0001 C CNN
	1    1650 4925
	-1   0    0    -1  
$EndComp
Text Label 2025 4475 2    50   ~ 0
REF
Wire Wire Line
	2825 4675 2825 5350
Wire Wire Line
	2025 5350 2025 5200
Wire Wire Line
	2125 5350 2025 5350
Text Label 2125 5350 0    50   ~ 0
ADC1P
Text Label 2700 5350 2    50   ~ 0
ADC1N
Wire Wire Line
	2825 5350 2700 5350
$Comp
L Device:R R?
U 1 1 5FB92A24
P 1275 4675
F 0 "R?" H 1350 4825 50  0000 C CNN
F 1 "100k" V 1275 4675 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" V 1205 4675 50  0001 C CNN
F 3 "~" H 1275 4675 50  0001 C CNN
	1    1275 4675
	-1   0    0    1   
$EndComp
$Comp
L Device:C_Small C?
U 1 1 5FB92A2A
P 1050 4675
F 0 "C?" H 1150 4725 50  0000 L CNN
F 1 "1uF" H 1150 4650 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1050 4675 50  0001 C CNN
F 3 "~" H 1050 4675 50  0001 C CNN
	1    1050 4675
	-1   0    0    -1  
$EndComp
Wire Wire Line
	2025 4375 1150 4375
Wire Wire Line
	1150 4375 1150 4500
Wire Wire Line
	1150 4500 1050 4500
Wire Wire Line
	1275 4500 1275 4525
Wire Wire Line
	1050 4575 1050 4500
Wire Wire Line
	1050 4775 1050 4925
Wire Wire Line
	1050 4925 1150 4925
Wire Wire Line
	1275 4925 1275 4825
Wire Wire Line
	1150 4925 1150 5200
Wire Wire Line
	1150 5200 2025 5200
Connection ~ 1150 4925
Wire Wire Line
	1150 4925 1275 4925
Connection ~ 2025 5200
Wire Wire Line
	2025 5200 2025 4675
Wire Wire Line
	1150 4250 1150 4375
Connection ~ 1150 4375
Connection ~ 1150 4500
Wire Wire Line
	1150 4500 1275 4500
$Comp
L power:GNDA #PWR?
U 1 1 5FB92A42
P 3100 4575
F 0 "#PWR?" H 3100 4325 50  0001 C CNN
F 1 "GNDA" H 3105 4402 50  0000 C CNN
F 2 "" H 3100 4575 50  0001 C CNN
F 3 "" H 3100 4575 50  0001 C CNN
	1    3100 4575
	-1   0    0    -1  
$EndComp
Wire Wire Line
	2825 4575 2925 4575
Wire Wire Line
	2825 4475 2925 4475
Wire Wire Line
	2925 4475 2925 4575
Connection ~ 2925 4575
Wire Wire Line
	2925 4575 3100 4575
$Comp
L power:+3V0 #PWR?
U 1 1 5FB92A4D
P 2925 4300
F 0 "#PWR?" H 2925 4150 50  0001 C CNN
F 1 "+3V0" H 2940 4473 50  0000 C CNN
F 2 "" H 2925 4300 50  0001 C CNN
F 3 "" H 2925 4300 50  0001 C CNN
	1    2925 4300
	1    0    0    -1  
$EndComp
Wire Wire Line
	2925 4300 2925 4375
Wire Wire Line
	2925 4375 2825 4375
$Comp
L power:VDDA #PWR?
U 1 1 5FB92A55
P 1650 4525
F 0 "#PWR?" H 1650 4375 50  0001 C CNN
F 1 "VDDA" H 1500 4600 50  0000 C CNN
F 2 "" H 1650 4525 50  0001 C CNN
F 3 "" H 1650 4525 50  0001 C CNN
	1    1650 4525
	1    0    0    -1  
$EndComp
Wire Wire Line
	1650 4525 1650 4575
Wire Wire Line
	2025 4575 1650 4575
Wire Wire Line
	1650 4650 1650 4575
Connection ~ 1650 4575
Wire Wire Line
	1650 4850 1650 4925
Text Label 1150 3575 1    50   ~ 0
VBias
Wire Wire Line
	1150 3575 1150 3750
Wire Wire Line
	2050 2600 2050 3100
Wire Wire Line
	1075 2850 1175 2850
Wire Wire Line
	2050 3100 1175 3100
Wire Wire Line
	1175 3100 1175 2850
Connection ~ 2050 3100
Connection ~ 1175 2850
Wire Wire Line
	1175 2850 1300 2850
Wire Wire Line
	2950 2500 3075 2500
Wire Wire Line
	3075 2500 3075 2625
Connection ~ 2950 2500
$EndSCHEMATC
