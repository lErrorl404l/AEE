#include "..\..\script_component.hpp"
/*
Camouflage and material properties (issue #119).

Resolves the uniform's CAMOUFLAGE/MATERIAL signature: solar absorptivity
(colour), NIR reflectance (the NVG black-hole effect), permeability
(wind penetration) and emissivity (thermal).  The INSULATION (clo) is a
separate concern - it lives with the garment type in
fnc_getUniformProperties (the per-slot split).

The classname is classified by FAMILY keywords - the codebase's
dynamic pattern (uniform names vary across mods; the family is the
stable signal).  A camouflage pattern IS a combat uniform; the pattern
keywords (the full Camopedia inventory) drive the NIR class.

Arguments:
  0: unit (OBJECT, default player)

Returns [alphaSolar, nirReflectance, permeability, emissivity]
  alphaSolar - solar absorptivity 0..1 (colour)
  nirReflectance - NIR reflectance 0..1 (the NVG black-hole effect)
  permeability - fabric permeability 0..1 (wind penetration)
  emissivity   - thermal emissivity 8-14 um (fabric ~0.93)
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [0.7, 0.35, 0.5, 0.93] };

private _uniform = uniform _unit;
if (_uniform == "") exitWith { [0.7, 0.35, 0.5, 0.93] };

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

// Classname + DISPLAYNAME family classification.  The displayName is
// the player-facing string (configFile >> CfgWeapons >> class >>
// displayName) - it carries the garment-type keywords every mod uses,
// including mods whose CLASSNAMES are opaque (e.g. Zulu's
// avteg_unione_uniform = "[AvTEG] Uniform (1)", UKSF G3, Winter
// Parka).  The family keywords cover vanilla + the verified major mod
// conventions (RHS acu/cu/g3/m88/flora/emr, afghanka/6sh122/gorka,
// abu/flcu; Zulu/UKSF G3/Smock/Parka).  The combined string is
// classified, so a uniform with a combat classname AND a winter
// displayName resolves to the displayName's garment type.
private _uni = toLower (_uniform + " " + getText (configFile >> "CfgWeapons" >> _uniform >> "displayName"));
private _res = switch (true) do {
    case (_uni find "ghillie" >= 0):  { [0.70, 0.45, 0.30, 0.93] };
    case (_uni find "wet" >= 0 ||
          _uni find "diver" >= 0):    { [0.85, 0.35, 0.05, 0.95] };
    case (_uni find "snow" >= 0 ||
          _uni find "schneetarn" >= 0 ||
          _uni find "overwhite" >= 0):     { [0.55, 0.45, 0.15, 0.93] };
    // The combat fallback: any CAMO PATTERN or field colour is a
    // combat uniform.  Garment-type words (smock, fleece, parka,
    // coverall) classify INSULATION in fnc_getUniformProperties, not
    // the camouflage pattern.  Garment/uniform-TYPE words (acu, g3,
    // m88, bdu, frog - the Crye cuts and uniform families) classify
    // INSULATION in fnc_getUniformProperties, not the pattern.
    case (_uni find "combat" >= 0 ||
          _uni find "flora" >= 0 ||
          _uni find "emr" >= 0 ||
          // camo-pattern names: a camouflage pattern IS a combat
          // uniform.  The complete global inventory (Camopedia index,
          // verified): UK MTP/BTP/DPM, US Multicam/OCP/UCP/ERDL/
          // MARPAT/AOR/DCU/chocolate-chip, Europe Flecktarn/
          // Tropentarn/Vegetato/M90/M05/wz.93/Pantera/Splinter/
          // Alpenflage/Lizard, Russia TTsKO/VSR/EMR/Flora/KLMK/
          // Gorka/Partizan/Surak/Recon, Asia Tigerstripe/AUSCAM/
          // CADPAT, commercial PenCott/ATACS/Kryptek.
          _uni find "mtp" >= 0 ||
          _uni find "btp" >= 0 ||
          _uni find "dpm" >= 0 ||
          _uni find "multicam" >= 0 ||
          _uni find "mcam" >= 0 ||
          _uni find "ocp" >= 0 ||
          _uni find "ucp" >= 0 ||
          _uni find "m81" >= 0 ||
          _uni find "erdl" >= 0 ||
          _uni find "marpat" >= 0 ||
          _uni find "aor" >= 0 ||
          _uni find "dcu" >= 0 ||
          _uni find "chocolate" >= 0 ||
          _uni find "flecktarn" >= 0 ||
          _uni find "tropentarn" >= 0 ||
          _uni find "vegetato" >= 0 ||
          _uni find "m90" >= 0 ||
          _uni find "m05" >= 0 ||
          _uni find "pantera" >= 0 ||
          _uni find "splinter" >= 0 ||
          _uni find "alpen" >= 0 ||
          _uni find "lizard" >= 0 ||
          _uni find "ttsko" >= 0 ||
          _uni find "vsr" >= 0 ||
          _uni find "emr" >= 0 ||
          _uni find "klmk" >= 0 ||
          _uni find "partizan" >= 0 ||
          _uni find "surak" >= 0 ||
          _uni find "tigerstripe" >= 0 ||
          _uni find "tiger" >= 0 ||
          _uni find "auscam" >= 0 ||
          _uni find "cadpat" >= 0 ||
          _uni find "pencott" >= 0 ||
          _uni find "atacs" >= 0 ||
          _uni find "kryptek" >= 0 ||
          _uni find "reed" >= 0 ||
          _uni find "woodland" >= 0 ||
          // the complete camo inventory (Camopedia 1152-pattern dump):
          // brushstroke, denison, duck, jigsaw, oakleaf, berezka/birch,
          // strichtarn, raindrop, frogskin, amoeba, spotted/mottled,
          // digital/pixelated, mountain/rocky, desert/tan, tiger/leopard
          _uni find "brushstroke" >= 0 ||
          _uni find "denison" >= 0 ||
          _uni find "duck" >= 0 ||
          _uni find "jigsaw" >= 0 ||
          _uni find "oakleaf" >= 0 ||
          _uni find "berezka" >= 0 ||
          _uni find "birch" >= 0 ||
          _uni find "strichtarn" >= 0 ||
          _uni find "raindrop" >= 0 ||
          _uni find "frogskin" >= 0 ||
          _uni find "amoeba" >= 0 ||
          _uni find "mottled" >= 0 ||
          _uni find "spotted" >= 0 ||
          _uni find "pixel" >= 0 ||
          _uni find "digital" >= 0 ||
          // the modern (2010-2026) universal patterns: the
          // Multicam-family successors adopted worldwide
          _uni find "multitarn" >= 0 ||
          _uni find "multiterreno" >= 0 ||
          _uni find "amcu" >= 0 ||
          _uni find "scorpion" >= 0 ||
          _uni find "oef" >= 0 ||
          _uni find "us4ces" >= 0 ||
          _uni find "vkpo" >= 0 ||
          _uni find "izlom" >= 0 ||
          _uni find "mm14" >= 0 ||
          _uni find "mm25" >= 0 ||
          _uni find "ratnik" >= 0 ||
          _uni find "m18" >= 0 ||
          _uni find "m23" >= 0 ||
          _uni find "m2017" >= 0 ||
          _uni find "loreng" >= 0 ||
          _uni find "tiuna" >= 0 ||
          _uni find "patriot" >= 0 ||
          _uni find "spec4ce" >= 0 ||
          _uni find "mountain" >= 0 ||
          _uni find "rocky" >= 0 ||
          _uni find "desert" >= 0 ||
          _uni find "tan" >= 0 ||
          _uni find "leopard" >= 0 ||
          _uni find "rhodesian" >= 0 ||
          _uni find "splinter" >= 0 ||
          // generic pattern descriptors (all combat): blotch/splotch,
          // spot/spotted, stripe/stripes, leaf/leaves, dots, geometric,
          // puzzle, waves, vertical stripes, maze, cellular
          _uni find "blotch" >= 0 ||
          _uni find "splotch" >= 0 ||
          _uni find "spot" >= 0 ||
          _uni find "stripe" >= 0 ||
          _uni find "leaf" >= 0 ||
          _uni find "dots" >= 0 ||
          _uni find "geometric" >= 0 ||
          _uni find "puzzle" >= 0 ||
          _uni find "waves" >= 0 ||
          _uni find "vertical" >= 0 ||
          _uni find "maze" >= 0 ||
          _uni find "cellular" >= 0 ||
          // solid colours: an olive/khaki/tan uniform is a combat
          // uniform (the global standard field colour, e.g. RHS GREF
          // nat_olive, the Israeli/Olive-field nations)
          _uni find "olive" >= 0 ||
          // the final combat fallback: any name still carrying a
          // pattern/camo marker IS a combat uniform (country-prefixed
          // generic names, language variants: camuflaje/tarn/tenue,
          // "national guard pattern" etc - all from the Camopedia dump)
          _uni find "pattern" >= 0 ||
          _uni find "camo" >= 0 ||
          _uni find "camuflaje" >= 0 ||
          _uni find "camuflado" >= 0 ||
          _uni find "tarn" >= 0 ||
          _uni find "tenue" >= 0 ||
          _uni find "uniform" >= 0):   { [0.80, 0.40, 0.35, 0.93] };
    default                           { [0.70, 0.40, 0.35, 0.93] };
};

missionNamespace setVariable [QGVAR(clothingCache), [_frame, _res]];
_res

