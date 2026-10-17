# World Magnetic Model 2025

`WMM2025.COF` and `WMM2025_TestValues.txt` are the unmodified NOAA NCEI /
British Geological Survey files from
https://www.ncei.noaa.gov/sites/default/files/2024-12/WMM2025COF.zip
(released 2024-12-17, valid 2025.0-2030.0). WMM is produced by the US
government (NOAA NCEI and the NGA) with the UK BGS and is in the public
domain in the United States.

`tools/gen_wmm.py` projects the coefficients to
`addons/magnetism/functions/fnc_wmmField.sqf` and refuses to write unless
the SQF kernel, executed by the test harness, reproduces every NOAA test
value.
