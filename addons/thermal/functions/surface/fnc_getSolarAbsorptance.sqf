#include "..\..\script_component.hpp"
/*
Per-selection camo colour -> solar absorptance (issue #124).

Visible colour drives SOLAR heating (absorptance alpha in the visible
band) but NOT LWIR emissivity: painted surfaces all emit ~0.9 in 8-14
um regardless of colour (FLIR T505002 paint table 0.88-0.96 SW /
0.92-0.94 LW).  A black vehicle heats faster in the sun than a tan one,
but both show the same emissivity once heated - alpha sets the heating
RATE, eps sets the emission.

The absorptance is resolved PER SELECTION because a unit is not one
colour: the uniform, vest, helmet, goggles, and gloves each carry their
own texture source (desert tan / woodland green / black / olive), and a
vehicle's body, turret, and wheels each carry their own paint.  Reading
the object's active texture per selection gives each clothing item or
panel its own solar loading.

Colour source: the selection's ACTIVE texture path (getObjectTextures),
which for a unit reflects the worn clothing item's texture.  Reference
bands (NASA TP-2005-212792 absorptance tables):

  white / snow / light sand   0.15 - 0.35   (Z93 white 0.14-0.17)
  tan / desert / light green  0.45 - 0.60
  woodland / olive / dark green 0.60 - 0.75
  black / very dark           0.85 - 0.96   (black paint 0.90-0.96)

Arguments:
  0: object (OBJECT) - the unit or vehicle
  1: selection index (NUMBER) - which model selection to read
  2: fallback texture (STRING, optional) - texture path to classify if
     the selection's texture is empty

Return Value:
  NUMBER solar absorptance alpha, 0..1 (default 0.70)
*/

params [
    ["_obj", objNull, [objNull]],
    ["_selIdx", 0, [0]],
    ["_fallbackTex", "", [""]]
];
if (isNull _obj) exitWith { 0.70 };

private _alpha = 0.70;
private _tex = _fallbackTex;
private _texs = getObjectTextures _obj;
if (_selIdx >= 0 && {_selIdx < (count _texs)}) then {
    if ((_texs select _selIdx) isNotEqualTo "") then {
        _tex = _texs select _selIdx;
    };
};
_tex = toLower _tex;

if (_tex find "black" >= 0) then {
    _alpha = 0.90;
} else {
    if (_tex find "white" >= 0 || {_tex find "snow" >= 0}) then {
        _alpha = 0.20;
    } else {
        if (_tex find "sand" >= 0 || {_tex find "tan" >= 0} || {_tex find "desert" >= 0}) then {
            _alpha = 0.50;
        } else {
            if (_tex find "olive" >= 0 || {_tex find "green" >= 0} || {_tex find "wood" >= 0}) then {
                _alpha = 0.70;
            };
        };
    };
};

_alpha
