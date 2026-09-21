#include "..\script_component.hpp"
/*
Protection derivation (issue #170).

DERIVES the real STANAG 4569 protection of a vehicle from its mass and
class hierarchy — the dynamic layer on top of the #168 table.  A new
mod vehicle is classified by getMass + isKindOf automatically: the real
protection scales with mass and role.

  mass + hierarchy -> protection category -> STANAG level -> the RHA
  equivalent (the #168 conversion curve)

The mass->protection bands (from the researched vehicle data, issue
#168): a 60-ton MBT sits in the 500-900 mm RHAe band, a 12-ton IFV in
L4-L5, a 5-ton truck in L0.  The category bands are the researched
mass->protection curves; the #168 specific-variant table OVERRIDES the
derivation where it matters (DU vs export Abrams - a table entry beats
a mass estimate).

Arguments:
  0: vehicle (OBJECT, default the player's vehicle)

Returns [stanagLevel, rhaEquivalentMm, defeats] - the derived
protection, with the #168 table taking precedence when it resolves the
class.
*/
params [["_vehicle", vehicle player, [objNull]]];
if (isNull _vehicle) exitWith { [0, 0, "none"] };

// The #168 table is authoritative when it resolves the class (the
// specific-variant data beats the mass estimate - a DU Abrams and an
// export Abrams differ).
private _tableResult = [_vehicle] call FUNC(getVehicleArmour);
if ((_tableResult select 1) > 0) exitWith { _tableResult };

// ─── The mass-based derivation ───────────────────────────────────────────
// getMass (kg, engine-computed from the model + cargo) is the real
// physical mass.  The class hierarchy gives the role.  The bands:
//   truck / car (soft skin):   L0, <10 mm RHA
//   protected patrol (LSV):    L2, ~20 mm (7.62 API)
//   wheeled APC:               L4, ~60 mm (14.5 mm)
//   tracked APC:               L3, ~40 mm (7.62 AP)
//   IFV:                       L5, ~120 mm (25 mm APDS)
//   SPAAG:                     L5, ~100 mm
//   MBT:                       L6, ~650 mm (30 mm APFSDS / KE)
//   artillery/SAM:             L4, ~50 mm
private _mass = getMass _vehicle;   // kg
if (_mass <= 0) then { _mass = 10000; };   // fallback: a 10-ton vehicle

// The hierarchy check (most specific first - the isKindOf chain).
if (_vehicle isKindOf "Tank") exitWith { [6, 650, "120mmKE"] };
if (_vehicle isKindOf "APC_Tracked_01_base_F" || _vehicle isKindOf "APC_Tracked_02_base_F"
    || _vehicle isKindOf "APC_Tracked_03_base_F") exitWith {
    if (_mass > 20000) then { [5, 120, "25mm"] } else { [3, 40, "7.62AP"] }
};
if (_vehicle isKindOf "APC_Wheeled_01_base_F" || _vehicle isKindOf "APC_Wheeled_02_base_F"
    || _vehicle isKindOf "APC_Wheeled_03_base_F") exitWith {
    if (_mass > 15000) then { [5, 100, "25mm"] } else { [4, 60, "14.5mm"] }
};
if (_vehicle isKindOf "Car") exitWith {
    if (_mass > 8000) then { [2, 20, "7.62API"] } else { [0, 5, "7.62ball"] }
};
if (_vehicle isKindOf "Truck") exitWith { [0, 5, "7.62ball"] };
if (_vehicle isKindOf "Air") exitWith { [0, 3, "7.62ball"] };   // aircraft skin

// Default: the mass bands without a recognised hierarchy.
if (_mass > 50000) then { [6, 650, "120mmKE"] }
else { if (_mass > 15000) then { [4, 60, "14.5mm"] }
    else { if (_mass > 8000) then { [2, 20, "7.62API"] } else { [0, 5, "7.62ball"] } }
}
