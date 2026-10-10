#include "..\script_component.hpp"

/*
Source frequency spectrum (acoustic propagation data layer).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps a sound-event kind to a 9-octave-band spectrum in dB per band.  The
peak band carries the broadband source level from fnc_acousticSourceDb, so the
absolute loudness has ONE source of truth; this kernel supplies only the
per-band SHAPE.  An unknown kind is silent, matching fnc_acousticSourceDb.

SOURCED: the peak-band level, from fnc_acousticSourceDb.
UNSOURCED: the per-band shape.  No public source states a weapon or engine
octave-band spectrum, so the five shapes below are modelling choices, ordered
by the issue #80 archetypes: a gunshot is broadband with a 125-2000 Hz peak, a
suppressed shot is cut above 1 kHz, an explosion and an engine are low-band
dominant, a footstep is quiet and mid-band.  Each shape is an offset in dB
from the peak band, so the peak is 0.  The absolute level comes from the
source table, so a shape never sets loudness on its own.

Bands: 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz.

Arguments:
  0: String - the event kind (gunshot, suppressed, explosion, grenade,
     aircraft, vehicle, footstep)

Returns:
  Array - 9 rows, each [frequency Hz, source level dB], low band first

Example:
  "gunshot" call aee_ambience_fnc_acousticSpectrum
Public: Yes
*/

params [
    ["_kind", "", [""]]
];

private _bands = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000];
private _peakDb = [_kind] call FUNC(acousticSourceDb);

// Per-band offset from the peak band, dB.  UNSOURCED modelling choice.
private _key = toLower _kind;
private _offsets = [0, 0, 0, 0, 0, 0, 0, 0, 0];
if (_key == "gunshot") then { _offsets = [-20, -12, -3, 0, 0, -2, -8, -18, -30]; };
if (_key == "grenade") then { _offsets = [-20, -12, -3, 0, 0, -2, -8, -18, -30]; };
if (_key == "suppressed") then { _offsets = [-20, -12, -3, 0, 0, -27, -33, -43, -55]; };
if (_key == "explosion") then { _offsets = [0, -4, -12, -24, -36, -46, -54, -60, -66]; };
if (_key == "vehicle") then { _offsets = [0, -3, -10, -20, -32, -44, -52, -58, -62]; };
if (_key == "aircraft") then { _offsets = [0, -3, -10, -20, -32, -44, -52, -58, -62]; };
if (_key == "footstep") then { _offsets = [-26, -14, -4, 0, -6, -16, -28, -40, -50]; };

private _out = [];
for "_i" from 0 to ((count _bands) - 1) do {
    _out pushBack [(_bands select _i), (_peakDb + (_offsets select _i))];
};

_out
