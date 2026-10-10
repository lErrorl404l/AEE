#include "..\script_component.hpp"

/*
ISO 9613-1 octave-band absorption table (acoustic propagation).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It builds the 9-octave-band absorption table for one weather state by calling
fnc_atmosphericAbsorption per band.  A caller recomputes the table on each
weather update, so it tracks the temperature, the humidity and the pressure.

The nine bands are the standard octave-band centres 31.5 Hz to 8 kHz.  The
band set is the issue #80 spectrum layout, shared with fnc_acousticSpectrum,
so the source spectrum and the absorption table align band for band.

Arguments:
  0: Number - the air temperature, degrees Celsius
  1: Number - the relative humidity, percent 0 to 100
  2: Number - the atmospheric pressure, hPa (default 1013.25)

Returns:
  Array - 9 rows, each [frequency Hz, absorption dB per metre], low band first

Example:
  [15, 50, 1013.25] call aee_ambience_fnc_atmosphericAbsorptionTable
Public: Yes
*/

params [
    ["_temperatureC", 15, [0]],
    ["_humidity", 50, [0]],
    ["_pressureHPa", 1013.25, [0]]
];

private _bands = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000];
private _out = [];
{
    _out pushBack [_x, ([_x, _temperatureC, _humidity, _pressureHPa] call FUNC(atmosphericAbsorption))];
} forEach _bands;

_out
