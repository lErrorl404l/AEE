#include "..\..\script_component.hpp"
/*
Thermal detector band resolver (aee-thermal-realism T1).

Maps a band token to its band edges in metres.  This kernel is pure.

  lwir  8-14 um  uncooled microbolometer / VOx, and the cooled MCT Catherine-MP
                 LW, which is a long-wave detector
  mwir  3-5 um   cooled InSb, and the cooled MWIR MCT devices Sophie Ultima,
                 FLIR Recon V and Safran JIM LR

The band is per-device.  It is a field in the device corpus
(data/device/catalogue/thermal_devices.json) sourced from the detector class in
docs/wiki/research/sensor-device-library.md.  It is NOT derived from the
`cooled` flag: a cooled MCT can be either band.

An unknown token returns the LWIR pair.  LWIR is the sane default and the
honest one: most fielded thermal devices are uncooled LWIR.

Arguments:
  0: bandToken (STRING, "lwir" or "mwir", default "lwir")

Return Value: ARRAY [lambda1M, lambda2M], the band edges in metres.
Example: ["mwir"] call aee_thermal_fnc_resolveThermalBand
Public: No
*/
params [["_bandToken", "lwir", [""]]];

if ((toLower _bandToken) == "mwir") exitWith { [3e-6, 5e-6] };
[8e-6, 14e-6]
