#include "..\..\script_component.hpp"
/*
 * ECOTI HUD range/altitude formatter (pure kernel).
 *
 * Metres below one kilometre, one-decimal kilometres at and above it.
 * Used by the rangefinder readout and the marker distance labels.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_mapMarkers.sqf
 * (FPANO_ECOTI_fnc_formatDistance).
 *
 * Params:
 *   0: _dist (SCALAR) - distance in metres.
 *
 * Returns: STRING, the display distance.
 */
params [["_dist", 0, [0]]];

private _text = (str (round _dist)) + "m";
if (_dist >= 1000) then {
    _text = ((_dist / 1000) toFixed 1) + "km";
};

_text
