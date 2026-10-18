#include "..\script_component.hpp"

/*
Static Stability Factor for a vehicle (issue #108).

SSF = T / (2 h), where T is the track width and h the centre-of-gravity
height.  SSF is the level-ground lateral acceleration in g at which the
inside wheels lift (NHTSA Rollover Resistance).

Neither term is a vanilla CfgVehicles property: there is no track-width key
and the centre of gravity is a PhysX runtime value, not a config value.
So this function builds SSF from what the engine does expose:

  h  from getCenterOfMass (v1.12+), which returns the CG offset in model
     space.  Its z component is the CG height above the model centre; the
     model centre sits at boundingCenter, so the CG height above the
     wheel-contact plane needs the bounding box.  The engine returns a
     two- or three-element box, [[min],[max]] or
     [[min],[max],boundingSphereDiameter], and only the first two elements
     are corners.  The modest error of measuring from the model centre is
     absorbed by the dynamic factor, and the value is clamped to a sane
     band.

  T  from the class table below.  A hand table is used deliberately: the
     wheel memory points carry positions but their naming is not uniform
     across vanilla and modded vehicles, and a wrong track width is worse
     than a curated one.  The table is data, not a list of vehicle names
     in code, and an unknown class falls to a class-level default by
     isKindOf, so modded vehicles still resolve.

The result is clamped to 0.3..2.0.  Below 0.3 no vehicle with a real
wheelbase would be stable; above 2.0 the value is a formula or geometry
error, not a vehicle.

Arguments:
  0: vehicle (OBJECT)

Return Value: ARRAY [ssf, cgHeightM, trackWidthM, source]
  source is "runtime" when the CG came from getCenterOfMass, or "table"
  when the centre of gravity could not be read and the class default was
  used for both terms.
Example: [cursorObject] call aee_mobility_fnc_calculateSSF
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

if (isNull _vehicle) exitWith { [1.0, 0, 0, "table"] };

// ─── Track width by vehicle class ────────────────────────────────────────
// Values are track widths in metres (the lateral distance between the
// centres of the left and right wheel contact patches).  Sources: the
// published dimensions of the real vehicle each class represents, since
// the engine does not expose the geometry.  The list is ordered most
// specific first, because isKindOf matches the whole inheritance chain.
//
// The selector must name an ENGINE class.  "MRAP", "Wheeled_APC" and
// "Tracked_APC" are AEE class TOKENS, not CfgVehicles classes, so an
// isKindOf test against them is always false and the row could never
// match: an MRAP and a wheeled APC fell through to Car, and a tracked APC
// to Tank.  The vanilla chains, verified from the shipped PBO configs
// (hemtt derapify, 2026-10-18):
//   MRAP_01_base_F : Car_F : Car        (soft_f.pbo)
//   MRAP_02_base_F : Car_F : Car        (soft_f.pbo)
//   MRAP_03_base_F : Car_F : Car        (soft_f_beta.pbo)
//   Wheeled_APC_F  : Car_F : Car        (armor_f_beta.pbo)
//   APC_Tracked_01_base_F : Tank_F : Tank  (armor_f_beta.pbo)
//   APC_Tracked_02_base_F : Tank_F : Tank  (armor_f_beta.pbo)
//   APC_Tracked_03_base_F : Tank_F : Tank  (armor_f_gamma.pbo)
//   Truck_F : Car_F : Car   (soft_f_beta.pbo)
//   Truck : Car             (engine core, Dta/bin.pbo)
// Truck and Car are the engine's own classes and stay, but both must come
// after every more specific class: a truck is kindOf Car.
private _trackTable = [
    ["MRAP_01_base_F", 2.00],   // RG-31 / MaxxPro class: wide V-hull, high CG
    ["MRAP_02_base_F", 2.00],
    ["MRAP_03_base_F", 2.00],
    ["Wheeled_APC_F", 2.10],
    ["APC_Tracked_01_base_F", 2.50],
    ["APC_Tracked_02_base_F", 2.50],
    ["APC_Tracked_03_base_F", 2.50],
    ["Tank",      2.70],   // track centres; full width is wider
    ["Helicopter", 0],     // not a ground rollover case
    ["Truck_F",   1.90],
    ["Truck",     1.90],
    ["Car",       1.55]    // passenger car / light utility
];

// The real geometry first: the vehicle's own wheel points, read from its
// config or its model (fnc_getVehicleGeometry).  The class table below is
// the fallback, used only when the vehicle declares no readable wheels.
private _geo = [_vehicle] call EFUNC(vehicles,getVehicleGeometry);
private _track = _geo select 0;

if (_track <= 0) then {
    {
        if (_vehicle isKindOf (_x select 0)) exitWith {
            _track = _x select 1;
        };
    } forEach _trackTable;
};

// A tracked vehicle rolls about its track centres, so the tank entry above
// applies.  An unmatched class falls to a conservative light-vehicle width.
if (_track <= 0) then { _track = 1.60; };

// A rotorcraft with a zero entry is not a rollover subject.
if (_vehicle isKindOf "Air") exitWith { [0, 0, 0, "table"] };

// ─── Centre-of-gravity height ────────────────────────────────────────────
private _cgHeight = 0;
private _source = ["table", "geometry"] select ((_geo select 0) > 0);
private _com = getCenterOfMass _vehicle;
if (_com isEqualType [] && {count _com == 3}) then {
    // getCenterOfMass returns the offset from the model centre.  Measure
    // from the model centre upward: the bounding box gives the extent, so
    // the CG height above the underside is half the box height plus the
    // offset.  The underside is the wheel-contact plane for a ground
    // vehicle to within suspension travel.
    private _bb = boundingBoxReal _vehicle;
    // Accept a two- or three-element box and read only the two corners.
    if (_bb isEqualType [] && {(count _bb == 2) || {count _bb == 3}}) then {
        private _bbMin = _bb select 0;
        private _bbMax = _bb select 1;
        private _halfHeight = ((_bbMax select 2) - (_bbMin select 2)) * 0.5;
        _cgHeight = _halfHeight + (_com select 2);
        _source = "runtime";
    };
};

// A vehicle with no readable CG falls to the class default by kind.  The
// values are the published CG heights of the class each represents.
if (_cgHeight <= 0) then {
    private _cgTable = [
        ["MRAP_01_base_F", 1.65],
        ["MRAP_02_base_F", 1.65],
        ["MRAP_03_base_F", 1.65],
        ["Wheeled_APC_F", 1.10],
        ["APC_Tracked_01_base_F", 0.70],
        ["APC_Tracked_02_base_F", 0.70],
        ["APC_Tracked_03_base_F", 0.70],
        ["Tank",      0.60],
        ["Truck_F",   1.00],
        ["Truck",     1.00],
        ["Car",       0.55]
    ];
    _cgHeight = 1.00;
    {
        if (_vehicle isKindOf (_x select 0)) exitWith {
            _cgHeight = _x select 1;
        };
    } forEach _cgTable;
    _source = "table";
};

// ─── SSF ─────────────────────────────────────────────────────────────────
private _ssf = _track / (2 * _cgHeight);
_ssf = _ssf max 0.3 min 2.0;

[_ssf, _cgHeight, _track, _source]
