#include "..\script_component.hpp"
/*
Vehicle identity classifier (issue #117).

Function: aee_mobility_fnc_classifyVehicle.

The classifier is the single identity surface for a ground vehicle. It
composes the name matcher aee_mobility_fnc_getVehicleMatch with the
generated property band table aee_mobility_fnc_getVehicleBands.

It resolves in this order.

  corpus   aee_mobility_fnc_getVehicleMatch resolves the class by its name.
           The result is a catalogue identity.
  band     the live properties select a catalogue entry. The band table is
           filtered by the live vehicle type, then by the nearest held
           operating weight, then by the nearest held extent. A tie at the
           nearest extent selects no row, so the classifier never guesses
           between two catalogue entries. This is the route for a class
           whose display name is a fictional Arma designation.
  token    the class is the first ground token it isKindOf, most specific
           first. This is the coarse class identity and the type source.
           It is the same token order aee_mobility_fnc_calculateSSF uses.
  none     no route resolved. The class token is empty. The classifier
           never returns a wrong catalogue entry.

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
private _vehicleType = ["wheeled", "tracked"] select _tracked;

private _classToken = "";
private _matchedBy = "none";
private _resolved = false;

// ─── Corpus: the name routes ─────────────────────────────────────────────
if (!(_match isEqualType []) || (count _match != 7)) then {
    _match = [_type] call FUNC(getVehicleMatch);
};
if ((_match isEqualType []) && ((count _match) == 7)) then {
    _classToken = _match select 0;
    _vehicleType = _match select 2;
    _matchedBy = "corpus";
    _resolved = true;
};

// ─── Band: the live properties ───────────────────────────────────────────
// Pass one finds the nearest held operating weight among the rows of the
// live vehicle type. Pass two finds the nearest held extent among the rows
// at that weight. A tie at the extent selects no row.
if (!_resolved && (_massKg > 0)) then {
    private _rows = call FUNC(getVehicleBands);
    private _minMass = -1;
    {
        _x params ["_cid", "_rowType", "_rowTracked", "_rowMass"];
        if ((_rowType == _vehicleType) && (_rowMass > 0)) then {
            private _distance = abs (_rowMass - _massKg);
            if ((_minMass < 0) || (_distance < _minMass)) then { _minMass = _distance; };
        };
    } forEach _rows;
    if (_minMass >= 0) then {
        private _minExtent = -1;
        private _hits = 0;
        private _best = [];
        {
            _x params ["_cid", "_rowType", "_rowTracked", "_rowMass", "_rowLen", "_rowWid", "_rowHgt"];
            if ((_rowType == _vehicleType) && (_rowMass > 0)
                && (abs (_rowMass - _massKg) == _minMass)) then {
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
if (!_resolved) then {
    private _groundTokens = [
        "MRAP", "Wheeled_APC", "Tank", "Tracked_APC", "Car", "Truck", "Wheeled_APC_F"
    ];
    {
        if (_vehicle isKindOf _x) exitWith { _classToken = _x; };
    } forEach _groundTokens;
    if (_classToken != "") then { _matchedBy = "token"; };
};

[_classToken, _vehicleType, _tracked, _hasTurret, _massKg, _lengthM, _widthM, _heightM, _matchedBy]
