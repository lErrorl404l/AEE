#include "..\..\script_component.hpp"

/*
Fragmentation warhead parameters (issue #107).

Each row: [key, chargeMassKg, casingMassKg, sqrt2E, geometry, fragmentCount].

  M67 grenade   400 g total, 184 g Composition B (US Army FM 23-30); sphere.
  M107 155 mm   43.2 kg shell, 6.86 kg TNT (TM 9-1300-203); cylinder.
  Mk 82 500 lb  227 kg bomb, 87 kg Tritonal (NAVAIR 11-1-4); cylinder.
  RPG-7 PG-7V   2.6 kg, 730 g OKFOL (HMX-based); cylinder.

The fragment count is the Mott total count N0.  M67 uses N0 = 1440, chosen so
the mean fragment mass M_casing / N0 = 0.15 g sits inside the published
0.1-0.2 g band and N(m > 0.5 g) = 109.  The other counts follow the issue:
M107 about 2000, Mk 82 about 10000, RPG-7 about 400.

Input:  _key (string)
Output: [chargeMassKg, casingMassKg, sqrt2E, geometry, fragmentCount], or []
        when the key is unknown
*/
params [["_key", "", [""]]];

private _table = [
    ["M67",  0.184, 0.216,  2700, "sphere",   1440],
    ["M107", 6.86,  36.34,  2370, "cylinder", 2000],
    ["Mk82", 87,    140,    2320, "cylinder", 10000],
    ["RPG7", 0.730, 1.87,   2900, "cylinder", 400]
];

private _row = [];
private _i = 0;
private _n = count _table;
while { _i < _n } do {
    private _candidate = _table select _i;
    if ((_candidate select 0) == _key) then { _row = _candidate; };
    _i = _i + 1;
};
_row
