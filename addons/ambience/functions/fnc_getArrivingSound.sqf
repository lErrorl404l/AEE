#include "..\script_component.hpp"

/*
Arriving sound spectrum (acoustic propagation).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It propagates a source spectrum to one listener and returns the arriving
per-band level in dB.  It is the frequency-resolved companion of
fnc_acousticLevel: it uses the SAME spherical-spreading law (20*log10 of the
distance) and the SAME weather propagation index, and adds the ISO 9613-1
atmospheric absorption per band.  It does not restate the spreading model.

Model, per band:
  arriving = sourceDb - 20*log10(d / index) - alpha(f) * d - occlusionDb
  - Spherical spreading: 20*log10(d), the inverse-square law.  SOURCED.
  - Weather index: the effective range scales by 1/index, exactly as
    fnc_acousticLevel scales its effective distance.  The index is AEE's
    published model aee_weather_currentSoundPropagation (0.3 to 2.0), computed
    by fnc_updateSoundPropagation.  SOURCED (the repo model), not restated.
  - Atmospheric absorption: alpha(f) from fnc_atmosphericAbsorption, ISO
    9613-1.  SOURCED.  This is the frequency-dependent term the broadband
    model lacks.
  - Occlusion: the caller's terrain loss in dB, applied flat across the bands.
    UNSOURCED, the same convention fnc_acousticLevel uses.

Arguments:
  0: Array  - the source spectrum, rows [frequency Hz, source dB]
  1: Number - the listener distance, metres
  2: Number - the propagation index, 0.3 to 2.0
  3: Array  - the absorption table, rows [frequency Hz, dB per metre]
  4: Number - the occlusion loss, dB (default 0)

Returns:
  Array - one [frequency Hz, arriving dB] row per source band

Example:
  [spectrum, 2000, 1.2, alphaTable, 6] call aee_ambience_fnc_getArrivingSound
Public: Yes
*/

params [
    ["_spectrum", [], [[]]],
    ["_distance", 0, [0]],
    ["_propagationIndex", 1, [0]],
    ["_absorptionTable", [], [[]]],
    ["_occlusionDb", 0, [0]]
];

private _index = (_propagationIndex max 0.3) min 2.0;
private _effective = (_distance / _index) max 1;
private _spreadDb = 20 * (log _effective);

private _out = [];
{
    private _band = _x;
    private _freq = _band select 0;
    private _sourceDb = _band select 1;

    // Match the absorption row by frequency.  A missing band absorbs nothing.
    private _alpha = 0;
    {
        if ((_x select 0) == _freq) then { _alpha = _x select 1; };
    } forEach _absorptionTable;

    private _arriving = _sourceDb - _spreadDb - (_alpha * _distance) - _occlusionDb;
    _out pushBack [_freq, _arriving];
} forEach _spectrum;

_out
