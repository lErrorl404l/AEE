#include "..\script_component.hpp"

/*
Density altitude from pressure altitude and outside air temperature.

Density altitude is the pressure altitude corrected for a non-standard air
temperature.  The FAA rule of thumb adds 120 ft of density altitude for every
degree Celsius the air is warmer than ISA, and subtracts 120 ft for every
degree colder:

    DA = PA + 120 * (OAT - ISA_T),   ISA_T = 15 - 1.98 * (PA / 1000 ft)

1.98 C per 1000 ft is the ISA lapse rate of 6.5 C per 1000 m.  In SI the rule
is 36.576 m of density altitude per degree C and the lapse term is 0.0065 C
per metre.

Source: FAA Pilot's Handbook of Aeronautical Knowledge, Ch. 11 (Density
Altitude).  ISA lapse rate 6.5 C/km and sea-level 15 C: ICAO Doc 7488 / ISO
2533.

This is a pure kernel: no missionNamespace, no GVAR or EGVAR, no engine
command.

Arguments:
  0: NUMBER - pressure altitude, metres
  1: NUMBER - outside air temperature, degrees Celsius

Return Value: NUMBER - density altitude, metres
Example: [2400, 30] call aee_flight_fnc_calculateDensityAltitude
Public: No
*/

params [
    ["_pressureAltitudeM", 0, [0]],
    ["_oatC", 15, [0]]
];

// ISA temperature at the pressure altitude, then the FAA correction.
private _isaTempC = 15 - 0.0065 * _pressureAltitudeM;
private _deltaC = _oatC - _isaTempC;

_pressureAltitudeM + 36.576 * _deltaC
