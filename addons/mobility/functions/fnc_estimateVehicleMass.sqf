#include "..\script_component.hpp"

/*
Vehicle mass estimate wrapper (issue #117).

Function: aee_mobility_fnc_estimateVehicleMass.

This function is a lookup surface. It reads engine state and returns a
seven-element result. It never drives the vehicle and it never writes a
catalogue value.

The order is sourced-first and fail-closed:

  1. A null vehicle or an empty class returns unavailable.
  2. A sourced catalogue row with an operating weight wins. The model does
     not run.
  3. The CBA setting and the generated approval flag must both be on. If
     either is off, the result is unavailable.
  4. The bounding box gives the length, width and height. The engine returns
     a two- or three-element box, [[min],[max]] or
     [[min],[max],boundingSphereDiameter]. Only the first two elements are
     corners. An extent outside the model geometry band is refused.
  5. Declared hiddenSelectionsMaterials give the material signal. One
     distinct non-ground class narrows the density. More than one distinct
     class is a disagreement. No material, or only the ground residual,
     uses the mass-class default density.
  6. The generated mass-class table resolves the density class and the fill
     range, in the order token, vehicle type, default. A matched row is used
     only when its fill range is usable. A zero-fill or inverted row is
     skipped, so the search continues to a later row. An empty token row
     therefore cannot shadow a later calibrated vehicle-type row.
  7. The core computes the bounded range.
  8. The power check runs only when the model power block is enabled. It is
     disabled until an in-engine probe records the band.
  9. The integer codes map to text, seven status variables are published,
     and the seven-element result is returned.

Return Value: ARRAY
  [lowKg, highKg, method, assumptions, confidence, status, source]
  A sourced row returns lowKg == highKg and status "sourced". A modelled
  range returns lowKg < highKg and status "estimated". Every other path
  returns [0, 0, 0, "none", "none", "unavailable", "none"].

Published (aee_mobility_vehicleMass*):
  LowKg, HighKg, Method, Assumptions, Confidence, Status, Source.

Arguments:
  0: _vehicle (OBJECT) a ground vehicle

Example: [cursorObject] call aee_mobility_fnc_estimateVehicleMass
Public: No
*/

params [["_vehicle", objNull, [objNull]]];

// Publish the seven status variables and return the seven-element result.
// Every path returns through this helper, so the two always agree.
private _publish = {
    params ["_low", "_high", "_method", "_assumptions", "_confidence", "_status", "_source"];
    GVAR(vehicleMassLowKg) = _low;
    GVAR(vehicleMassHighKg) = _high;
    GVAR(vehicleMassMethod) = _method;
    GVAR(vehicleMassAssumptions) = _assumptions;
    GVAR(vehicleMassConfidence) = _confidence;
    GVAR(vehicleMassStatus) = _status;
    GVAR(vehicleMassSource) = _source;
    [_low, _high, _method, _assumptions, _confidence, _status, _source]
};

private _unavailable = {
    [0, 0, 0, "none", "none", "unavailable", "none"] call _publish
};

// ─── 1. Null and type guard ──────────────────────────────────────────────
if (isNull _vehicle) exitWith { call _unavailable };

private _type = typeOf _vehicle;
if (_type == "") exitWith { call _unavailable };

// ─── 2. Sourced path. A catalogue weight always wins. ────────────────────
private _match = [_type] call FUNC(getVehicleMatch);
private _srcWeight = 0;
private _srcId = "";
if (_match isNotEqualTo []) then {
    _srcWeight = (_match select 6) select 0;
    _srcId = _match select 5;
};

if (_srcWeight > 0) exitWith {
    [_srcWeight, _srcWeight, "catalogue_row",
     "derived: operating weight read from the sourced catalogue row",
     "documented", "sourced", _srcId] call _publish
};

// ─── 3. Setting and approval gate ────────────────────────────────────────
private _model = call FUNC(getVehicleMassModel);
private _approved = (_model select 0) isEqualTo true;
private _settingOn = GVAR(estimateVehicleMassEnabled) isEqualTo true;

if (!_settingOn || !_approved) exitWith {
    call _unavailable
};

private _densityTable = _model select 1;
private _classTable = _model select 2;
private _geometryBands = _model select 3;
private _powerBlock = _model select 4;

private _minExtentM = _geometryBands select 0;
private _maxExtentM = _geometryBands select 1;
private _maxWidthRatio = _geometryBands select 2;

// ─── 4. Bounding-box extents ─────────────────────────────────────────────
private _lengthM = 0;
private _widthM = 0;
private _heightM = 0;
private _geometryOk = false;
private _box = boundingBoxReal _vehicle;

// The engine returns a two-element box [[min],[max]] or a three-element box
// [[min],[max],boundingSphereDiameter]. Only the first two elements are
// corners, so accept either arity and read only those two.
if ((_box isEqualType []) && {(count _box == 2) || {count _box == 3}}
    && {(_box select 0) isEqualType []} && {(_box select 1) isEqualType []}) then {
    private _boxMin = _box select 0;
    private _boxMax = _box select 1;
    _lengthM = abs ((_boxMax select 0) - (_boxMin select 0));
    _widthM = abs ((_boxMax select 1) - (_boxMin select 1));
    _heightM = abs ((_boxMax select 2) - (_boxMin select 2));
    _geometryOk = (_lengthM >= _minExtentM) && (_lengthM <= _maxExtentM)
        && (_widthM >= _minExtentM) && (_widthM <= _maxExtentM)
        && (_heightM >= _minExtentM) && (_heightM <= _maxExtentM);
};

if (!_geometryOk) exitWith { call _unavailable };

// ─── 5. Declared material signal ─────────────────────────────────────────
// Only the config-declared hiddenSelectionsMaterials are read. A selection
// count is never a mass fraction. The engine does not expose per-selection
// default materials, so the signal only narrows when it is unambiguous.
private _selectionMaterials = getArray (configOf _vehicle >> "hiddenSelectionsMaterials");
private _materialClasses = [];
{
    private _path = toLower _x;
    if ((_path != "") && (_path != "any")) then {
        private _materialClass = [_x] call EFUNC(material,getSurfaceMaterial);
        if (_materialClass != "" && {!(_materialClass in _materialClasses)}) then {
            _materialClasses pushBack _materialClass;
        };
    };
} forEach _selectionMaterials;

// 0 default, 1 one declared class, 2 declared disagreement,
// 3 ground residual only.
private _materialNarrowed = 0;
private _declaredClass = "";
private _classCount = count _materialClasses;
if (_classCount == 1) then {
    private _onlyClass = _materialClasses select 0;
    if (_onlyClass == "ground") then {
        _materialNarrowed = 3;
    } else {
        _materialNarrowed = 1;
        _declaredClass = _onlyClass;
    };
} else {
    if (_classCount > 1) then {
        _materialNarrowed = 2;
    };
};

// ─── 6. Mass-class resolution ────────────────────────────────────────────
// Token, then vehicle type, then default. The generated table keeps the
// default row last. A matched row is stored only when its fill range is
// usable. A zero-fill or inverted row is skipped, so the search continues
// and an empty token row cannot shadow a calibrated vehicle-type row.
private _vehicleType = "wheeled";
if (_vehicle isKindOf "Tank" || {_vehicle isKindOf "Tracked_APC"}) then {
    _vehicleType = "tracked";
};

private _classRow = [];
{
    _x params ["_key", "_matchKind", "_rowType", "_rowDensity", "_rowFillLow", "_rowFillHigh"];
    // Usable means a positive, ordered fill range. The core refuses a
    // zero-fill or inverted row, so the wrapper must not select one.
    private _rowUsable = (_rowFillLow > 0) && (_rowFillHigh > 0)
        && (_rowFillLow <= _rowFillHigh);
    if (_rowUsable && {_classRow isEqualTo []}) then {
        private _rowMatch = false;
        if (_matchKind == "token") then {
            _rowMatch = _vehicle isKindOf _key;
        } else {
            if (_matchKind == "vehicle_type") then {
                _rowMatch = (_rowType == _vehicleType);
            } else {
                _rowMatch = true;
            };
        };
        if (_rowMatch) then { _classRow = _x; };
    };
} forEach _classTable;

if (_classRow isEqualTo []) exitWith { call _unavailable };

private _fillLow = _classRow select 4;
private _fillHigh = _classRow select 5;

// ─── 7. Density and fill lookup ──────────────────────────────────────────
private _densityClass = _classRow select 3;
if (_declaredClass != "") then { _densityClass = _declaredClass; };

private _rhoLow = 0;
private _rhoHigh = 0;
{
    if ((_x select 0) == _densityClass) exitWith {
        _rhoLow = _x select 1;
        _rhoHigh = _x select 2;
    };
} forEach _densityTable;

if ((_rhoLow <= 0) || (_rhoHigh <= 0)) exitWith { call _unavailable };

// ─── 8. Power branch. Disabled without a recorded band. ──────────────────
private _enginePower = 0;
private _powerEnabled = 0;
private _powerLow = 0;
private _powerHigh = 0;
private _powerHardFactor = _powerBlock select 2;

if ((_powerBlock select 0) isEqualTo true) then {
    // enginePower is a PhysX tuning value. It is passed to the core only as
    // a corroborating band bound, never as a mass. The branch stays closed
    // until an in-engine probe records the band.
    _enginePower = getNumber (configFile >> "CfgVehicles" >> _type >> "enginePower");
    private _powerBands = _powerBlock select 3;
    private _bandLow = 0;
    private _bandHigh = 0;
    if ((count _powerBands) == 2 && {(_powerBands select 0) isEqualType 0}) then {
        _bandLow = _powerBands select 0;
        _bandHigh = _powerBands select 1;
    } else {
        {
            if ((_x isEqualType []) && {count _x == 2}) then {
                private _bandKey = toLower (_x select 0);
                if (_bandKey == "low") then { _bandLow = _x select 1; };
                if (_bandKey == "high") then { _bandHigh = _x select 1; };
            };
        } forEach _powerBands;
    };
    if ((_bandLow > 0) && (_bandHigh > _bandLow)) then {
        _powerEnabled = 1;
        _powerLow = _bandLow;
        _powerHigh = _bandHigh;
    };
};

private _read = [
    _lengthM, _widthM, _heightM,
    _rhoLow, _rhoHigh,
    _fillLow, _fillHigh,
    _enginePower, _powerEnabled,
    _powerLow, _powerHigh, _powerHardFactor,
    _maxWidthRatio, _materialNarrowed
] call FUNC(estimateVehicleMassCore);

// ─── 9. Code mapping and publication ─────────────────────────────────────
private _low = _read select 0;
private _high = _read select 1;
private _statusCode = _read select 5;

// A point mass is not a range, and a failed core is not an estimate.
if ((_statusCode != 1) || (_low <= 0) || (_high <= _low)) exitWith {
    call _unavailable
};

private _methodCode = _read select 2;
private _mask = _read select 3;
private _confidenceCode = _read select 4;

private _method = "none";
if (_methodCode == 1) then { _method = "geometry_material"; };
if (_methodCode == 2) then { _method = "geometry_material_power"; };

private _confidence = "none";
if (_confidenceCode == 1) then { _confidence = "low"; };
if (_confidenceCode == 2) then { _confidence = "medium"; };
if (_confidenceCode == 3) then { _confidence = "high"; };

private _assumptionTable = [
    [1, "geometry_box"],
    [2, "box_includes_mirrors"],
    [4, "material_declared"],
    [8, "material_class_default"],
    [16, "density_cited"],
    [32, "fill_calibrated"],
    [64, "power_disabled"],
    [128, "power_in_band"],
    [256, "power_out_band"],
    [512, "residual_ground_not_trusted"],
    [1024, "material_disagreement"]
];
private _assumptions = "";
{
    _x params ["_bit", "_name"];
    if ((_mask % (_bit * 2)) >= _bit) then {
        if (_assumptions != "") then { _assumptions = _assumptions + "|"; };
        _assumptions = _assumptions + _name;
    };
} forEach _assumptionTable;
if (_assumptions == "") then { _assumptions = "none"; };

[_low, _high, _method, _assumptions, _confidence, "estimated",
 "modelled: box volume times calibrated fill times cited density"] call _publish
