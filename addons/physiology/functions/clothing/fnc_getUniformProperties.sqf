#include "..\..\script_component.hpp"
/*
Uniform properties (issue #119).

Returns the uniform slot's [weight kg, armor NIJ 0..3, nirReflectance,
clo].  The uniform carries the base garment (4.0 kg), its worn gloves
(no separate engine slot - the glove signal rides in the uniform
classname, e.g. the UKSF/Zulu "_KP_P" scheme, Mechanix/Oakley gloves),
and its insulation (the garment type: combat 0.75, winter 2.50, flight
0.65, wet 1.50, ghillie 1.20, light 0.50 clo).

The CAMOUFLAGE signature (alphaSolar, NIR, permeability, emissivity)
is a separate concern - fnc_getCamouflageProperties (the per-slot
split).  Glove insulation (Gonzalez 1998: light 0.86, heavy 1.05,
mitten 1.46 clo) adds to the uniform clo.

Arguments:
  0: unit (OBJECT, default player)

Returns [weight, armor, nirReflectance, clo].
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [4.5, 0, 0.40, 0.75] };

private _camo = [_unit] call FUNC(getCamouflageProperties);   // [alpha, nir, perm, emiss]
private _nir = _camo select 1;
private _gloves = [_unit] call FUNC(getGloveProperties);

// The uniform's own insulation from its garment type (the classname +
// displayName, the same family pattern as the camo classifier).  The
// garment-type words (smock, parka, fleece, coverall, fatigues,
// gorka, ecwcs) classify the INSULATION - they are clothing types,
// not camouflage patterns.
private _uniform = uniform _unit;
private _uni = toLower (_uniform + " " + getText (configFile >> "CfgWeapons" >> _uniform >> "displayName"));
private _clo = switch (true) do {
    case (_uni find "ghillie" >= 0):           { 1.20 };
    case (_uni find "wet" >= 0 ||
          _uni find "diver" >= 0):             { 1.50 };
    case (_uni find "winter" >= 0 ||
          _uni find "arctic" >= 0 ||
          _uni find "parka" >= 0 ||
          _uni find "gorka" >= 0 ||
          _uni find "6sh122" >= 0 ||
          _uni find "afghanka" >= 0 ||
          _uni find "klmk" >= 0 ||
          _uni find "snow" >= 0 ||
          _uni find "overwhite" >= 0 ||
          _uni find "ecwcs" >= 0 ||
          _uni find "anorak" >= 0 ||
          _uni find "fleece" >= 0 ||
          _uni find "insulat" >= 0 ||
          _uni find "cold" >= 0):               { 2.50 };
    case (_uni find "flight" >= 0 ||
          _uni find "pilot" >= 0 ||
          _uni find "abu" >= 0 ||
          _uni find "flcu" >= 0):               { 0.65 };
    // The combat fallback: any pattern/camo/olive/uniform name is a
    // standard combat uniform (clo 0.75).  The garment types (smock,
    // fatigues, coverall, jumpsuit, overall) are combat-wear.
    case (_uni find "camo" >= 0 ||
          _uni find "pattern" >= 0 ||
          _uni find "uniform" >= 0 ||
          _uni find "olive" >= 0 ||
          _uni find "combat" >= 0 ||
          _uni find "smock" >= 0 ||
          _uni find "fatigues" >= 0 ||
          _uni find "coverall" >= 0 ||
          _uni find "jumpsuit" >= 0 ||
          _uni find "overall" >= 0 ||
          // Crye G2/G3/G4 cuts + the RHS uniform families: these are
          // garment/uniform TYPES, not camouflage patterns.
          _uni find "acu" >= 0 ||
          _uni find "cu_" >= 0 ||
          _uni find "g2" >= 0 ||
          _uni find "g3" >= 0 ||
          _uni find "g4" >= 0 ||
          _uni find "m93" >= 0 ||
          _uni find "m88" >= 0 ||
          _uni find "bdu" >= 0 ||
          _uni find "sso" >= 0 ||
          _uni find "vdv" >= 0 ||
          _uni find "frog" >= 0 ||
          // the camo patterns are combat uniforms (insulation 0.75)
          _uni find "flora" >= 0 ||
          _uni find "emr" >= 0 ||
          _uni find "mtp" >= 0 ||
          _uni find "dpm" >= 0 ||
          _uni find "multicam" >= 0):           { 0.75 };
    default                                     { 0.50 };   // light shirt
};

// The uniform carries no armour (the vest covers the torso); its
// weight is the base garment (4.0 kg) + the gloves.  The researched item
// table outranks the base when a capture holds the uniform's family, and
// the gloves still ride in the uniform.
private _tier = [4.0 + _gloves, 0, _nir, _clo + _gloves];
private _mass = [_uniform, ["uniform", "garment"]] call FUNC(getItemMass);
if (_mass > 0) then { _tier set [0, _mass + _gloves] };
_tier
