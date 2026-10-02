#include "..\script_component.hpp"
/*
Vehicle identity classifier (issue #117).

Function: aee_mobility_fnc_classifyVehicle.

The classifier is the single identity surface for a vehicle. It composes
the name matcher aee_mobility_fnc_getVehicleMatch with the generated
property band table aee_mobility_fnc_getVehicleBands.

It resolves in this order.

  corpus   aee_mobility_fnc_getVehicleMatch resolves the class by its name.
           The result is a catalogue identity.
  band     the live properties select a catalogue entry. The band table is
           filtered by the live vehicle type, then by the nearest held
           operating weight, then by the nearest held extent. The nearest
           weight must stand out: two distinct held weights at the same
           distance, or a live weight outside the catalogue's own weight
           resolution, select no row. A tie at the nearest extent selects no
           row. This is the route for a class whose display name is a
           fictional Arma designation.
  token    the class is the first engine family token it isKindOf, most
           specific first. This is the coarse class identity and the type
           source. The ground order is the one aee_mobility_fnc_calculateSSF
           uses.
  none     no route resolved. The class token is empty. The classifier
           never returns a wrong catalogue entry.

A static weapon is not a vehicle. The base game declares class
StaticWeapon: LandVehicle, so the HMG, mortar, SAM and radar emplacements
would otherwise reach the band. The classifier returns no catalogue row for
a class that isKindOf "StaticWeapon".

Three vehicle families. The classifier acts on the engine roots LandVehicle,
Air and Ship. The catalogued route resolves a land, air or sea class alike.
The token route names the family: the ground tokens, then Helicopter and
Plane for air, then Ship for sea. The air and sea families carry the identity
geometry only. A soldier (CAManBase), a building, an animal and every other
non-vehicle is none of the three, so it resolves to none before every route.
A man on foot is the live case: the traction model reads `vehicle _unit`, and
on foot that is the man.

The live properties are the engine mass (getMass), the bounding box
(boundingBoxReal), the tracked flag (isKindOf Tank or Tracked_APC) and the
turret presence (allTurrets). The engine mass and the engine box are
identity signals for the band selector only. They are not sourced values
and they are never written to the catalogue.

Return Value: ARRAY [classToken, vehicleType, isTracked, hasTurret, massKg,
  lengthM, widthM, heightM, matchedBy].
  classToken   the catalogue id for the corpus and band routes, the engine
               ground token for the token route, empty for none.
  vehicleType  "wheeled" or "tracked".
  isTracked    the live tracked flag.
  hasTurret    true when the class declares at least one turret.
  massKg       the live engine mass in kilograms.
  lengthM      the live bounding-box length in metres.
  widthM       the live bounding-box width in metres.
  heightM      the live bounding-box height in metres.
  matchedBy    "corpus", "band", "token" or "none".

Arguments:
  0: vehicle (OBJECT) a ground vehicle, default objNull
  1: match (ARRAY, optional) a precomputed aee_mobility_fnc_getVehicleMatch
     result, default []. It avoids a second matcher run for a caller that
     already holds the match.

Example: [cursorObject] call aee_mobility_fnc_classifyVehicle
Public: No
*/

params [["_vehicle", objNull, [objNull]], ["_match", [], [[]]]];

if (isNull _vehicle) exitWith { ["", "wheeled", false, false, 0, 0, 0, 0, "none"] };

private _type = typeOf _vehicle;
if (_type == "") exitWith { ["", "wheeled", false, false, 0, 0, 0, 0, "none"] };

// A vehicle only. The classifier covers the three engine vehicle families:
// LandVehicle, Air and Ship. A soldier (CAManBase), a building, an animal
// and every other non-vehicle derives from none of the three, so it
// resolves to none before every route. A man on foot is the live case:
// `vehicle _unit` returns the man, and without this guard the band route
// would match the man's own engine mass to a light vehicle.
private _isLand = _vehicle isKindOf "LandVehicle";
private _isAir = _vehicle isKindOf "Air";
private _isSea = _vehicle isKindOf "Ship";
if !(_isLand || _isAir || _isSea) exitWith {
    ["", "wheeled", false, false, 0, 0, 0, 0, "none"]
};

// ─── Live observable properties ──────────────────────────────────────────
// The engine mass and the bounding box are the band selectors. They carry
// no sourced value.
private _massKg = getMass _vehicle;
private _lengthM = 0;
private _widthM = 0;
private _heightM = 0;
private _box = boundingBoxReal _vehicle;
if ((_box isEqualType []) && {(count _box == 2) || {count _box == 3}}
    && {(_box select 0) isEqualType []} && {(_box select 1) isEqualType []}) then {
    private _boxMin = _box select 0;
    private _boxMax = _box select 1;
    _lengthM = abs ((_boxMax select 0) - (_boxMin select 0));
    _widthM = abs ((_boxMax select 1) - (_boxMin select 1));
    _heightM = abs ((_boxMax select 2) - (_boxMin select 2));
};

private _tracked = (_vehicle isKindOf "Tank") || {_vehicle isKindOf "Tracked_APC"};
private _hasTurret = (count (allTurrets _vehicle)) > 0;
// The live family is the band selector. A land class is wheeled or tracked
// by its live tracked flag. An air class is air and a sea class is sea.
private _vehicleType = "wheeled";
if (_isSea) then {
    _vehicleType = "sea";
} else {
    if (_isAir) then {
        _vehicleType = "air";
    } else {
        _vehicleType = ["wheeled", "tracked"] select _tracked;
    };
};

// The tracked flag as a band row stores it, and the emplacement guard. A
// static weapon is not a vehicle, so the name routes, the band and the token
// route are all skipped and the classifier returns no catalogue row for it.
private _trackedFlag = [0, 1] select _tracked;
private _isEmplacement = _vehicle isKindOf "StaticWeapon";

private _classToken = "";
private _matchedBy = "none";
private _resolved = false;

// ─── Corpus: the name routes ─────────────────────────────────────────────
if (!_isEmplacement) then {
    if (!(_match isEqualType []) || (count _match != 7)) then {
        _match = [_type] call FUNC(getVehicleMatch);
    };
    if ((_match isEqualType []) && ((count _match) == 7)) then {
        _classToken = _match select 0;
        _vehicleType = _match select 2;
        _matchedBy = "corpus";
        _resolved = true;
    };
};

// ─── Band: the live properties ───────────────────────────────────────────
// Pass one finds the nearest held operating weight among the rows of the
// live vehicle type. Pass two finds the nearest held extent among the rows
// at that weight. A tie at the extent selects no row.
//
// The band is bounded. The live tracked flag must agree with the row. The
// nearest held weight must stand out: two distinct held weights at the same
// distance make it ambiguous and select no row. The live weight must also
// fall inside the catalogue's own weight resolution for the type, derived
// from the table: sort the held weights, take the relative gap between each
// consecutive pair, then the upper Tukey fence of those gaps (the standard
// 1.5 interquartile-range fence). No threshold is chosen by hand. A weight
// outside the fence is not plausibly the held vehicle, so its row is
// refused. The engine bounding box stays a tie-break only: the engine box
// axes do not align with the held length and width axes, so a magnitude
// test on the box would refuse valid rows.
if (!_resolved && !_isEmplacement && (_massKg > 0)) then {
    private _rows = call FUNC(getVehicleBands);

    private _heldMasses = [];
    {
        _x params ["_cid", "_rowType", "_rowTracked", "_rowMass"];
        if ((_rowType == _vehicleType) && (_rowMass > 0)) then {
            _heldMasses pushBack _rowMass;
        };
    } forEach _rows;
    _heldMasses sort true;

    private _gaps = [];
    for "_i" from 0 to ((count _heldMasses) - 2) do {
        private _low = _heldMasses select _i;
        if (_low > 0) then {
            _gaps pushBack (((_heldMasses select (_i + 1)) - _low) / _low);
        };
    };

    // A negative cap means too few gaps to measure a resolution, so no mass
    // bound applies. The real table always yields a positive cap.
    private _cap = -1;
    if ((count _gaps) >= 2) then {
        _gaps sort true;
        private _last = (count _gaps) - 1;
        private _q1 = _gaps select (floor (_last * 0.25));
        private _q3 = _gaps select (floor (_last * 0.75));
        _cap = _q3 + (1.5 * (_q3 - _q1));
    };

    // The nearest held weight, and whether two distinct held weights sit at
    // that same distance. Such a pair is ambiguous.
    private _minMass = -1;
    {
        private _distance = abs (_x - _massKg);
        if ((_minMass < 0) || (_distance < _minMass)) then { _minMass = _distance; };
    } forEach _heldMasses;

    private _nearValue = -1;
    private _nearCount = 0;
    {
        if (abs (_x - _massKg) == _minMass) then {
            if (_nearCount == 0) then {
                _nearValue = _x;
                _nearCount = 1;
            } else {
                if (_x != _nearValue) then { _nearCount = 2; };
            };
        };
    } forEach _heldMasses;

    if ((_minMass >= 0) && (_nearCount <= 1)) then {
        private _minExtent = -1;
        private _hits = 0;
        private _best = [];
        {
            _x params ["_cid", "_rowType", "_rowTracked", "_rowMass", "_rowLen", "_rowWid", "_rowHgt"];
            private _massDistance = abs (_rowMass - _massKg);
            if ((_rowType == _vehicleType) && (_rowTracked == _trackedFlag)
                && (_rowMass > 0) && (_massDistance == _minMass)
                && ((_cap < 0) || (_massDistance <= (_cap * _rowMass)))) then {
                private _extent = 0;
                if ((_rowLen > 0) && (_lengthM > 0)) then {
                    _extent = _extent + abs (_rowLen - _lengthM);
                };
                if ((_rowWid > 0) && (_widthM > 0)) then {
                    _extent = _extent + abs (_rowWid - _widthM);
                };
                if ((_rowHgt > 0) && (_heightM > 0)) then {
                    _extent = _extent + abs (_rowHgt - _heightM);
                };
                if ((_minExtent < 0) || (_extent < _minExtent)) then {
                    _minExtent = _extent;
                    _hits = 1;
                    _best = _x;
                } else {
                    if (_extent == _minExtent) then { _hits = _hits + 1; };
                };
            };
        } forEach _rows;
        if ((_hits == 1) && (_best isNotEqualTo [])) then {
            _classToken = _best select 0;
            _matchedBy = "band";
            _resolved = true;
        };
    };
};

// ─── Token: the coarse class identity ────────────────────────────────────
// Most specific first. The order follows the fnc_calculateSSF track table.
if (!_resolved && !_isEmplacement) then {
    // Most specific first, within each family. The ground order follows the
    // aee_mobility_fnc_calculateSSF track table. A class reaches one engine
    // family only, so the family order does not change a land match.
    private _vehicleTokens = [
        "MRAP", "Wheeled_APC", "Tank", "Tracked_APC", "Car", "Truck",
        "Wheeled_APC_F",
        "Helicopter", "Plane",
        "Ship"
    ];
    {
        if (_vehicle isKindOf _x) exitWith { _classToken = _x; };
    } forEach _vehicleTokens;
    if (_classToken != "") then { _matchedBy = "token"; };
};

[_classToken, _vehicleType, _tracked, _hasTurret, _massKg, _lengthM, _widthM, _heightM, _matchedBy]
