#include "..\..\script_component.hpp"

/*
Gurney fragment velocity from the charge-to-metal ratio (BRL Report 405, 1943).

The Gurney equation gives the terminal velocity of a metal casing driven by a
detonating charge, from the charge mass C and the casing mass M through the
Gurney constant sqrt(2E):

  cylinder (artillery shell)  V = sqrt(2E) / sqrt(M/C + 1/2)
  sphere   (grenade body)     V = sqrt(2E) / sqrt(M/C + 3/5)

The misremembered form V = sqrt(2E) * (M/C) / sqrt(1 + M/(2C)) keeps a leading
sqrt(M/C) factor that does not belong.  It gives about 6570 m/s for the M107
155 mm shell, which is impossible.  This function uses the two published
denominators directly.

Gurney constants sqrt(2E) (m/s) from BRL Report 405 and the standard table:
  TNT 2370, Composition B 2700, Tritonal 2320, RDX 2800, HMX 2900.

Input:  [_chargeMassKg, _casingMassKg, _sqrt2E, _geometry]
Output: fragment velocity (m/s)
*/
params [
    ["_chargeMassKg", 1, [0]],
    ["_casingMassKg", 1, [0]],
    ["_sqrt2E", 2370, [0]],
    ["_geometry", "cylinder", [""]]
];

if (_chargeMassKg <= 0 || _casingMassKg <= 0) exitWith { 0 };

private _ratio = _casingMassKg / _chargeMassKg;
private _offset = 0.5;                                // cylinder: M/C + 1/2
if (_geometry == "sphere") then { _offset = 0.6; };   // sphere: M/C + 3/5

_sqrt2E / sqrt (_ratio + _offset)
