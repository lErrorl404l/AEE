#include "..\..\script_component.hpp"
/*
Clothing insulation and camouflage (issue #119).

The layer between skin and environment.  Resolves a soldier's clothing
properties (clo insulation, solar absorptivity, NIR reflectance,
permeability, emissivity) from the uniform classname, with the
researched per-garment values (ASHRAE 55, ISO 11079, DLA camo
reflectance).

The classname is classified by FAMILY keywords - the codebase's
dynamic pattern (uniform names vary across mods; the family is the
stable signal):

  combat      -> standard combat uniform  (clo 0.75, alpha 0.80, NIR 0.40)
  winter/arctic -> ECWCS parka            (clo 2.50, alpha 0.55, NIR 0.45)
  flight/pilot -> flight suit            (clo 0.65, alpha 0.70, NIR 0.45)
  wet/diver   -> wet suit                (clo 1.50, alpha 0.85, NIR 0.35)
  ghillie     -> ghillie cover           (clo 1.20, alpha 0.70, NIR 0.45)
  default     -> light shirt             (clo 0.50, alpha 0.70, NIR 0.35)

The result is cached per uniform class (the per-frame cache pattern):
the classname rarely changes, and the optics/thermal readers call this
every frame.

Arguments:
  0: unit (OBJECT, default player)

Returns [clo, alphaSolar, nirReflectance, permeability, emissivity]
  clo       - insulation in clo (1 clo = 0.155 m2K/W)
  alphaSolar - solar absorptivity 0..1 (colour)
  nirReflectance - NIR reflectance 0..1 (the NVG black-hole effect)
  permeability - fabric permeability 0..1 (wind penetration)
  emissivity   - thermal emissivity 8-14 um (fabric ~0.93)
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [0.5, 0.7, 0.35, 0.5, 0.93] };

private _uniform = uniform _unit;
if (_uniform == "") exitWith { [0.5, 0.7, 0.35, 0.5, 0.93] };

// Per-frame cache: the uniform classname is stable.
private _frame = diag_frameNo;
private _cache = missionNamespace getVariable [QGVAR(clothingCache), []];
if (count _cache >= 2 && {(_cache select 0) == _frame}) exitWith {
    _cache select 1
};

// Explicit config override (CfgClothing) wins.  Walk the uniform's
// OWN inheritance chain (CfgWeapons ancestry): a modded uniform that
// inherits from a vanilla class (class MyUniform: U_B_CombatUniform_mcam)
// picks up the parent's CfgClothing entry through the chain.  This is
// the modded-support mechanism the issue requires.
private _candidate = configFile >> "CfgWeapons" >> _uniform;
private _depth = 0;
while {isClass _candidate && _depth < 16} do {
    private _cloth = configFile >> "CfgClothing" >> configName _candidate;
    if (isClass _cloth) exitWith {
        private _res = [
            getNumber (_cloth >> "clo"),
            getNumber (_cloth >> "alphaSolar"),
            getNumber (_cloth >> "nirReflectance"),
            getNumber (_cloth >> "permeability"),
            getNumber (_cloth >> "emissivity")
        ];
        missionNamespace setVariable [QGVAR(clothingCache), [_frame, _res]];
        _res
    };
    _candidate = inheritsFrom _candidate;
    _depth = _depth + 1;
};

// Classname family classification.  The family keywords cover the
// vanilla AND the major mod conventions (verified against RHS USAF/
// AFRF uniforms: acu/cu/g3/m88/flora/emr = combat, afghanka/6sh122/
// gorka = winter, abu/flcu = flight, wet/diver, ghillie).  Any
// uniform class that still carries no family keyword is the generic
// combat tier (0.75) - the safe default for a uniform.
private _uni = toLower _uniform;
private _res = switch (true) do {
    case (_uni find "ghillie" >= 0):  { [1.20, 0.70, 0.45, 0.30, 0.93] };
    case (_uni find "wet" >= 0 ||
          _uni find "diver" >= 0):    { [1.50, 0.85, 0.35, 0.05, 0.95] };
    case (_uni find "winter" >= 0 ||
          _uni find "arctic" >= 0 ||
          _uni find "parka" >= 0 ||
          _uni find "gorka" >= 0 ||
          _uni find "6sh122" >= 0 ||
          _uni find "afghanka" >= 0 ||
          _uni find "klmk" >= 0):     { [2.50, 0.55, 0.45, 0.15, 0.93] };
    case (_uni find "flight" >= 0 ||
          _uni find "pilot" >= 0 ||
          _uni find "abu" >= 0 ||
          _uni find "flcu" >= 0):     { [0.65, 0.70, 0.45, 0.30, 0.93] };
    case (_uni find "combat" >= 0 ||
          _uni find "fatigues" >= 0 ||
          _uni find "acu" >= 0 ||
          _uni find "cu_" >= 0 ||
          _uni find "g3_" >= 0 ||
          _uni find "m93" >= 0 ||
          _uni find "m88" >= 0 ||
          _uni find "bdu" >= 0 ||
          _uni find "flora" >= 0 ||
          _uni find "emr" >= 0 ||
          _uni find "sso" >= 0 ||
          _uni find "vdv" >= 0 ||
          _uni find "frog" >= 0):     { [0.75, 0.80, 0.40, 0.35, 0.93] };
    default                           { [0.75, 0.70, 0.40, 0.35, 0.93] };
};

missionNamespace setVariable [QGVAR(clothingCache), [_frame, _res]];
_res

