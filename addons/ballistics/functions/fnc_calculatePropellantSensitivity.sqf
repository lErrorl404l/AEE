#include "..\script_component.hpp"

/*
Resolve the propellant temperature sensitivity coefficient for an ammo type.

Units: fps per degree Fahrenheit, the reloading-litreature convention.
Real smokeless powders span ~0.14 to ~2.0 fps/degF:

  - Temperature-stable (Hodgdon Extreme, Alliant RL16/23/26): 0.14-0.5
  - Single-base extruded (nitrocellulose only):                 0.5-1.0
  - Central rule of thumb (most smokeless powders):              ~1.0
  - Double-base (nitrocellulose + nitroglycerin):                ~1.2-1.5
  - Double-base ball (military 5.56/7.62, WC844-type):          ~1.5
  - Most sensitive loads:                                         up to 2.0

The relative MV shift for a given coefficient depends on the round's own
muzzle velocity: a 9mm pistol at ~350 m/s shows a larger percentage shift
than a 5.56 rifle at ~905 m/s for the same powder.  This resolver returns
the coefficient only; fnc_calculateMuzzleVelocityCorrection applies it to
the ammo's real initSpeed.

Resolution cascade (first match wins):
  1. CfgAmmo >> ammo >> AEE_Propellant >> sensitivity   (mission/ammo author
     override, exact fps/degF)
  2. Built-in ammunition table keyed by CfgAmmo class (known cartridges)
  3. Propellant-type fallback                            (per-cartridge table
     by caliber family, e.g. "5.56" -> double-base ball 1.5)
  4. Central default 1.0 fps/degF                       (reload-litreature
     consensus; conservative for unknown ammo)

Notes:
  - The reference temperature is 21 degC (70 degF), the NATO EPVAT
    standard (AEP-97 / STANAG 4823) velocity-conditioning convention.
  - NASA SP-7413 is NOT a valid citation for this (it is a rocket-motor
    propellant-processing document, SP-8075); small-arms coefficients come
    from reloading literature and closed-vessel tests (Boulkadid et al.
    2016, DOI 10.22211/cejem/67229).

Input:  [_ammo]  - CfgAmmo classname (string)
Output: fps/degF coefficient (number)
*/

params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { 1.0 };

// ─── 1. Mission/ammo-author config override ───────────────────────────────
private _override = getNumber (configFile >> "CfgAmmo" >> _ammo >> "AEE_Propellant" >> "sensitivity");
if (_override > 0) exitWith { _override };

// ─── 2. Built-in ammunition table (known cartridges) ──────────────────────
// Keyed by the CfgAmmo class.  Coefficient in fps/degF.
private _AMMO_TABLE = createHashMapFromArray [
    // 5.56 NATO (M855-family, WC844 double-base ball)
    ["B_556x45_Ball",                1.5],
    ["B_556x45_Ball_Tracer_Red",     1.5],
    // 7.62 NATO (M80-family, double-base ball)
    ["B_762x51_Ball",                1.5],
    ["B_762x51_Ball_Tracer_Green",   1.5],
    // 9mm Parabellum (double-base)
    ["B_9x21_Ball",                  1.2],
    // 5.45mm (double-base ball)
    ["B_545x39_Ball",                1.5],
    // 6.5mm caseless (temperature-stable)
    ["B_65x39_Caseless",             0.3],
    // .338 Norma (temperature-stable match)
    ["B_338_NM_Ball",                0.3],
    // 12.7mm / .50 BMG (double-base ball)
    ["B_127x108_Ball",               1.5],
    ["B_127x99_Ball",                1.5]
];
private _tableHit = _AMMO_TABLE get _ammo;
if (!isNil "_tableHit") exitWith { _tableHit };

// ─── 3. Propellant-type fallback by cartridge family ───────────────────────
// Match common cartridge prefixes to the typical military/civilian powder.
private _caliber = _ammo;
private _typeCoeff = 1.0;   // central default (step 4, conservative)
if (_caliber find "556x45" >= 0) then { _typeCoeff = 1.5; };
if (_caliber find "762x51" >= 0) then { _typeCoeff = 1.5; };
if (_caliber find "545x39" >= 0) then { _typeCoeff = 1.5; };
if (_caliber find "127x" >= 0)   then { _typeCoeff = 1.5; };
if (_caliber find "9x21" >= 0)   then { _typeCoeff = 1.2; };
if (_caliber find "9x19" >= 0)   then { _typeCoeff = 1.2; };
if (_caliber find "338" >= 0)    then { _typeCoeff = 0.3; };
if (_caliber find "6.5" >= 0)    then { _typeCoeff = 0.3; };

_typeCoeff
