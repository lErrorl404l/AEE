#include "..\..\script_component.hpp"
/*
Goggles properties (issue #119).

Classifies the goggles slot (CfgGlasses G_ classes: eyewear, facewear,
respirators) by family keywords and returns [weight kg, armor NIJ 0..3,
nirReflectance, clo].  The values are the researched IRL figures from
equipment-library.md (eyewear/facewear table).

Groups (sortable by category -> company -> era):
  CBRN respirators | M50, M40, FM12/FM50/C50, S10, PMK-3, GP-5/7
    (~0.49-0.96 kg, CBRN Cap 1, face armour)
  Face protection  | mandibles, face shields, visors, MFS (frag-NIJ
    IIIA, ~0.30 kg)
  Face/neck cold   | balaclava, bandanna, shemagh, gaiter, scarf,
    hood (~0.10 kg, ~0.3 clo)
  Ballistic eyewear | ESS, Revision, Oakley, Wiley X (~0.03-0.13 kg,
    MIL-PRF-31013/32432)
  Sunglasses       | shades, aviator, lady, squares (no armour, dark
    lenses cut NIR)

Arguments:
  0: unit (OBJECT, default player)

Returns [weight, armor, nirReflectance, clo].
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [0.05, 0, 0.40, 0.02] };

private _goggleItem = goggles _unit;
if (_goggleItem == "") exitWith { [0.05, 0, 0.40, 0.02] };

private _goggleDef = [0.05, 0, 0.40, 0.02];
private _g = toLower _goggleItem;
switch (true) do {
    // ── CBRN respirators ──
    // M50 0.86 kg, FM12 0.79, PMK-3 0.96.  The mask is the heaviest
    // goggles-slot item and adds face armour.
    case (_g find "m50" >= 0 ||
          _g find "m40" >= 0 ||
          _g find "m42" >= 0 ||
          _g find "fm12" >= 0 ||
          _g find "fm50" >= 0 ||
          _g find "c50" >= 0 ||
          _g find "s10" >= 0 ||
          _g find "gp-5" >= 0 ||
          _g find "gp-7" >= 0 ||
          _g find "pmk" >= 0 ||
          _g find "respirator" >= 0): { [0.86, 1, 0.10, 0.08] };
    // ── Face protection (frag to NIJ IIIA) ──
    case (_g find "mandible" >= 0 ||
          _g find "faceshield" >= 0 ||
          _g find "visor" >= 0 ||
          _g find "mfs" >= 0):       { [0.30, 2, 0.10, 0.04] };
    // ── Face/neck cold protection (~0.3 clo) ──
    // Balaclava / bandanna / shemagh / gaiter / scarf / hood.  The
    // vanilla G_Balaclava_* and G_Bandanna_* families.
    case (_g find "balaclava" >= 0 ||
          _g find "bandanna" >= 0 ||
          _g find "shemag" >= 0 ||
          _g find "gaiter" >= 0 ||
          _g find "scarf" >= 0 ||
          _g find "hood" >= 0 ||
          _g find "lowprofile" >= 0): { [0.10, 0, 0.40, 0.30] };
    // ── Ballistic eyewear (MIL-PRF-31013/32432) ──
    // ESS/Revision/Oakley/Wiley X (~30-130 g).  Clear lenses keep NIR
    // transmissive.  The vanilla G_Combat/G_Tactical_* families.
    case (_g find "ess" >= 0 ||
          _g find "sawfly" >= 0 ||
          _g find "locust" >= 0 ||
          _g find "stingerhawk" >= 0 ||
          _g find "mframe" >= 0 ||
          _g find "crossbow" >= 0 ||
          _g find "landops" >= 0 ||
          _g find "wiley" >= 0 ||
          _g find "combat" >= 0 ||
          _g find "tactical" >= 0 ||
          _g find "spectacles" >= 0 ||
          _g find "sport" >= 0):     { [0.10, 1, 0.35, 0.01] };
    // ── Sunglasses (no armour, dark lenses cut NIR) ──
    case (_g find "shades" >= 0 ||
          _g find "aviator" >= 0 ||
          _g find "lady" >= 0 ||
          _g find "squares" >= 0):   { [0.03, 0, 0.10, 0.01] };
    // ── Generic goggles / glasses / diving ──
    case (_g find "goggle" >= 0 ||
          _g find "glasses" >= 0 ||
          _g find "diving" >= 0):    { [0.10, 1, 0.35, 0.01] };
    default                           { _goggleDef };
};
