#include "..\..\script_component.hpp"

/*
Fragmentation warhead parameters (issue #107).

Row: [key, chargeMassKg, casingMassKg, sqrt2E, geometry, fragmentCount].

Resolution order:

  1 the curated rows below, keyed exactly, which are the fallback for the
    munitions they were written for;
  2 the munition corpus, through aee_blast_fnc_getMunitionMatch, for a
    class the curated table does not name;
  3 an empty array when neither names the munition.

Curated rows, unchanged; each figure is the source's:

  M67 grenade   400 g total, 184 g Composition B (US Army FM 23-30); sphere.
  M107 155 mm   43.2 kg shell, 6.86 kg TNT (TM 9-1300-203); cylinder.
  Mk 82 500 lb  227 kg bomb, 87 kg Tritonal (NAVAIR 11-1-4); cylinder.
  RPG-7 PG-7V   2.6 kg, 730 g OKFOL (HMX-based); cylinder.

The M67 count is N0 = 1440, chosen so the mean fragment mass
M_casing / N0 = 0.15 g sits inside the published 0.1-0.2 g band. The other
counts follow the issue: M107 about 2000, Mk 82 about 10000, RPG-7 about
400.

A corpus row is derived from the entry that names the munition, one figure
per published field, and a labelled zero wherever the entry holds no figure:

  chargeMassKg    the entry's warhead_mass_kg, which is the explosive the
                  sources publish for a bomb, or its charge_mass_kg, the
                  filling weight, when the article gives that instead.
  casingMassKg    total_mass_kg - warhead_mass_kg, the case, when the entry
                  holds both.
  sqrt2E          the Gurney constant of the entry's filling, from the
                  register this kernel publishes (BRL Report 405): TNT 2370,
                  Composition B 2700, Tritonal 2320, RDX 2800, HMX 2900.
                  OKFOL 2900 is the figure the curated RPG-7 row uses for an
                  HMX-based filling. A filling the register does not publish
                  gives the labelled zero.
  geometry        "sphere" for a grenade, "cylinder" for every other type,
                  from the entry's munition_type.
  fragmentCount   the Mott total count N0 = casingMassKg / m_mean, with
                  m_mean the mean fragment mass the curated rows publish for
                  the geometry: 0.15 g for a sphere (the M67 row) and 14 g
                  for a cylinder (the Mk 82 row).

A missile body is not a driven casing. The corpus publishes a warhead weight
for a missile, not a casing mass, and a blast-fragmentation or
continuous-rod warhead is not a Mott case, so a missile row is the labelled
zero with an empty geometry. This function does not force the fragment model
onto such a round.

Input:  _key (string, a munition key or a game class name)
Output: [key, chargeMassKg, casingMassKg, sqrt2E, geometry, fragmentCount],
        or [] when neither the curated table nor the corpus names it
*/
params [["_key", "", [""]]];

private _table = [
    ["M67",  0.184, 0.216,  2700, "sphere",   1440],
    ["M107", 6.86,  36.34,  2370, "cylinder", 2000],
    ["Mk82", 87,    140,    2320, "cylinder", 10000],
    ["RPG7", 0.730, 1.87,   2900, "cylinder", 400]
];

private _lookup = {
    params ["_needle"];
    private _found = [];
    {
        if ((toLower (_x select 0)) == (toLower _needle)) then { _found = _x; };
    } forEach _table;
    _found
};

private _row = [_key] call _lookup;
if (_row isNotEqualTo []) exitWith { _row };

private _match = [_key] call FUNC(getMunitionMatch);
if (_match isEqualTo []) exitWith { [] };

// A corpus entry that is one of the curated munitions takes the curated row.
_row = [_match select 0] call _lookup;
if (_row isNotEqualTo []) exitWith { _row };

private _id = _match select 0;
private _type = _match select 1;
private _values = _match select 5;
private _totalMass = _values select 0;
private _warheadMass = _values select 1;
private _fillingMass = _values select 2;
private _filling = _values select 5;

if (_type == "missile") exitWith { [_id, 0, 0, 0, "", 0] };

private _chargeMass = 0;
if (_warheadMass > 0) then { _chargeMass = _warheadMass; };
if (_chargeMass == 0 && _fillingMass > 0) then { _chargeMass = _fillingMass; };

private _casingMass = 0;
if (_totalMass > 0 && _warheadMass > 0) then { _casingMass = _totalMass - _warheadMass; };
if (_casingMass < 0) then { _casingMass = 0; };

private _sqrt2E = 0;
{
    if ((_x select 0) == _filling) then { _sqrt2E = _x select 1; };
} forEach [
    ["TNT", 2370],
    ["Composition B", 2700],
    ["Tritonal", 2320],
    ["RDX", 2800],
    ["HMX", 2900],
    ["OKFOL", 2900]
];

private _geometry = "cylinder";
private _meanFragmentMass = 0.014;
if (_type == "grenade") then {
    _geometry = "sphere";
    _meanFragmentMass = 0.00015;
};

private _fragmentCount = 0;
if (_casingMass > 0) then { _fragmentCount = round (_casingMass / _meanFragmentMass); };

[_id, _chargeMass, _casingMass, _sqrt2E, _geometry, _fragmentCount]
