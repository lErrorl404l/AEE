#include "..\..\script_component.hpp"

/*
Star weather fade (aee-workshop-copy item 3, part 1).

The fade form is re-derived from fn_starNightTweaks.sqf in the Workshop mod
Star Light (Workshop 3749362906).  The mod ships no licence, so this is a
re-derived numeric form, not copied code.  The constants are UNSOURCED
aesthetic proxies.

Cloud and fog hide stars.  Each fade ramps from the full value at clear sky
to zero over a 0.05 band, then clamps to 0..value.  The result is the
smaller of the two fades.

  overcastFade = value * (0.5 - overcast) / 0.05   when overcast < 0.5, else 0
  fogFade      = value * (0.4 - fog) / 0.05        when fog < 0.40,     else 0

Arguments:
  0: Number - value to fade
  1: Number - engine overcast, 0..1
  2: Number - engine fog, 0..1

Returns:
  Number - faded value in 0..value
*/

params [
    ["_value", 0, [0]],
    ["_overcast", 0, [0]],
    ["_fog", 0, [0]]
];

private _overcastFade = 0;
if (_overcast < 0.5) then {
    _overcastFade = _value * ((0.5 - _overcast) / 0.05);
};

private _fogFade = 0;
if (_fog < 0.4) then {
    _fogFade = _value * ((0.4 - _fog) / 0.05);
};

_overcastFade = (_overcastFade max 0) min _value;
_fogFade = (_fogFade max 0) min _value;

(_overcastFade min _fogFade) min _value
