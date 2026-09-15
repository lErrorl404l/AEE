#include "..\script_component.hpp"

/*
Object surface temperature model for thermal vision rendering.

Each nearby object gets a surface temperature from its material, solar
exposure, engine state, movement, and convective cooling.  The results
feed thermal optics so vehicles, infantry, and terrain show realistic
heat signatures.

Physics basis:
  - Thermal inertia: every surface approaches its equilibrium
    temperature exponentially with a material time constant tau.
    Metal (vehicles) tau = 120 s, concrete/stone tau = 600 s,
    vegetation tau = 300 s, human body tau = 60 s.
  - Vehicle cold start: a running engine accumulates run time.  The
    body warms 40 C above ambient over ~5 min (tau = 300 s); the
    exhaust reaches 200 C above ambient within ~1 min (tau = 60 s).
    When the engine stops, the accumulated run time decays with
    tau = 300 s and the body cools back toward ambient.
  - Infantry clothing: the surface temperature interpolates between
    the body base temperature (33 C) and ambient by the clothing
    insulation factor (0.3 light tropical .. 0.8 arctic).  Movement
    adds metabolic heat (idle 0, walk 20, run 60, sprint 120 W).
    Wind chills exposed areas only.  The body acclimatises toward
    ambient over 30 min (tau = 1800 s).
  - Solar absorption: metal ~0.7, paint ~0.6, fabric ~0.5, skin ~0.6.
    Low thermal mass lets metal heat quickly in sun.
  - Wind cooling: convective cooling of ~2 C per m/s of wind, toward
    air temperature.
  - Shade: objects in shade lose solar heating and approach air
    temperature.
  - Emissivity: metal ~0.9, paint ~0.92, fabric ~0.95, skin ~0.98.
    Lower emissivity radiates less, so the radiant temperature drops.
  - Fog: dense fog scatters IR and pulls the apparent temperature
    toward ambient.
  - Ground: desert sand heats ~15 C above air, grass ~5 C, snow
    stays ~2 C below air.  Ground has thermal inertia too.

Persistent per-object state lives in QGVAR(thermalState), a hash map:
  key:   object reference (or "ground" for the area ground)
  value: [currentTemp, engineRunTime, lastUpdate, acclimatisation]
Stale entries (dead or deleted objects) are removed each tick.

Stored in GVAR(objectTemperatures) as [object, temperature] pairs, plus
GVAR(avgVehicleTemp), GVAR(avgInfantryTemp), and GVAR(avgGroundTemp).
*/

params [
    ["_center", objNull, [objNull, []]],
    ["_radius", 100, [0]],
    ["_maxObjects", 50, [0]]
];

// Defensive: nil center falls back to the current unit.
// Accepts BOTH objNull and [] (the env PFH and the calibration sweep call
// with bare `[] call`, which passes an empty array; the [objNull] type
// filter rejected it with "Type Array, expected Object").  After the
// fallback, _center is always the unit or objNull.
if (_center isEqualType []) then { _center = objNull; };
if (isNull _center) then {
    _center = call CBA_fnc_currentUnit;
};

// No unit on a dedicated server: publish empty state and stop
if (isNull _center) exitWith {
    missionNamespace setVariable [QEGVAR(core,objectTemperatures), []];
    missionNamespace setVariable [QEGVAR(core,avgVehicleTemp), 0];
    missionNamespace setVariable [QEGVAR(core,avgInfantryTemp), 0];
    missionNamespace setVariable [QEGVAR(core,avgGroundTemp), 0];
    0
};

_radius = _radius max 10 min 500;
_maxObjects = _maxObjects max 1 min 100;

// ─── Shared inputs ────────────────────────────────────────────────────────
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (isNil "_airTemp") then { _airTemp = 15; };
private _windSpeed = vectorMagnitude wind;
private _solar = [overcast] call EFUNC(core,calculateSolarRadiation);
private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
if (isNil "_fog") then { _fog = 0; };

// Clothing insulation setting (0.5 light .. 2.0 arctic) mapped to the
// surface-insulation fraction used by the clothing model (0.3..0.8).
private _insulationSetting = missionNamespace getVariable [QEGVAR(core,clothingInsulation), 1.0];
if (isNil "_insulationSetting") then { _insulationSetting = 1.0; };
private _insulation = 0.3 + 0.5 * ((_insulationSetting - 0.5) / 1.5);
_insulation = _insulation max 0.3 min 0.8;

// ─── Persistent thermal state ─────────────────────────────────────────────
private _thermalState = missionNamespace getVariable [QGVAR(thermalState), createHashMap];
private _now = diag_tickTime;

// ─── Ground temperature ───────────────────────────────────────────────────
private _groundType = toLower (surfaceType (getPos _center));
private _groundGain = switch (true) do {
    case (_groundType == "#gdtdesert"):     { 15 };
    case (_groundType == "#gdtsand"):       { 10 };
    case (_groundType == "#gdtice"):        { -2 };
    case (_groundType == "#gdtsnow"):       { -2 };
    case (_groundType == "#gdtconiferous"): {  2 };
    case (_groundType == "#gdtforest"):     {  3 };
    default                                 {  5 }; // grass
};
private _groundTau = switch (true) do {
    case (_groundType == "#gdtconiferous"): { 300 }; // vegetation
    case (_groundType == "#gdtforest"):     { 300 }; // vegetation
    default                                 { 600 }; // rock, sand, ice: slow
};

// Shade at the centre position: cast a ray straight up
private _centerASL = getPosASL _center;
private _eyePos = _centerASL vectorAdd [0, 0, 1.5];
private _abovePos = _eyePos vectorAdd [0, 0, 6];
private _hits = lineIntersectsSurfaces [_eyePos, _abovePos, objNull, objNull, true, 1, "GEOM", "NONE"];
private _groundTarget = _airTemp + _groundGain * _solar;
if (count _hits > 0) then { _groundTarget = _airTemp; };

// Convective cooling pulls the ground toward air temperature
_groundTarget = _groundTarget - _windSpeed * 2;
_groundTarget = _groundTarget max _airTemp;

// Ground thermal inertia: exponential approach to the target.  The
// step is the wall-clock delta since the last tick, clamped so a long
// pause cannot teleport the temperature.
private _groundState = _thermalState getOrDefault ["ground", [_airTemp, _now]];
private _groundTemp = _groundState select 0;
private _groundDt = ((_now - (_groundState select 1)) max diag_deltaTime) min 30;
_groundTemp = _groundTemp + (_groundTarget - _groundTemp) * (1 - exp (-_groundDt / _groundTau));
_thermalState set ["ground", [_groundTemp, _now]];

// ─── Object scan ──────────────────────────────────────────────────────────
private _objects = nearestObjects [_center, ["LandVehicle", "Air", "Ship", "Man", "StaticWeapon"], _radius];
if (count _objects > _maxObjects) then { _objects resize _maxObjects; };

private _results = [];
private _vehicleSum = 0;
private _vehicleCount = 0;
private _infantrySum = 0;
private _infantryCount = 0;

{
    if (isNull _x || {!alive _x}) then { continue; };
    private _obj = _x;

    // Shade: ray from above the object's top, ignoring its own geometry
    private _top = ((boundingBox _obj) select 1) select 2;
    private _objEye = (getPosASL _obj) vectorAdd [0, 0, (_top max 1) + 1];
    private _objAbove = _objEye vectorAdd [0, 0, 6];
    private _objHits = lineIntersectsSurfaces [_objEye, _objAbove, _obj, objNull, true, 1, "GEOM", "NONE"];
    private _inShade = count _objHits > 0;

    // Persistent state: [currentTemp, engineRunTime, lastUpdate, acclimatisation, objectRef]
    // Keys must be strings — SQF hashmaps reject Object references.
    private _objKey = str _obj;
    private _state = _thermalState getOrDefault [_objKey, []];
    private _hasState = count _state > 0;
    private _currentTemp = if (_hasState) then { _state select 0 } else { _airTemp };
    private _engineRunTime = if (_hasState) then { _state select 1 } else { 0 };
    private _acclimatisation = if (_hasState) then { _state select 3 } else { 33 };
    private _dt = if (_hasState) then { ((_now - (_state select 2)) max diag_deltaTime) min 30 } else { 0 };

    private _target = _airTemp;
    private _emissivity = 0.95;
    private _tau = 120;
    private _isInfantry = false;
    private _isVehicle = false;

    if (_obj isKindOf "Man") then {
        _isInfantry = true;
        if (!_hasState) then { _currentTemp = 33; }; // humans are always warm

        // Environmental acclimatisation: the body base temp drifts
        // toward ambient over 30 min (tau = 1800 s).
        _acclimatisation = _acclimatisation + (_airTemp - _acclimatisation) * (1 - exp (-_dt / 1800));

        // Clothing interpolates the surface between the body base and
        // ambient.  High insulation (arctic) keeps the surface warm.
        _target = _acclimatisation - (_acclimatisation - _airTemp) * (1 - _insulation);

        // Metabolic heat from movement: idle 0, walk 20, run 60, sprint 120 W.
        private _vSpeed = abs speed _obj;
        private _metabolicHeat = switch (true) do {
            case (_vSpeed > 6):   { 120 };
            case (_vSpeed > 3):   {  60 };
            case (_vSpeed > 0.5): {  20 };
            default               {   0 };
        };
        _target = _target + _metabolicHeat * 0.05;

        // Solar gain on exposed skin, scaled by the exposed fraction.
        if (!_inShade) then { _target = _target + _solar * 0.6 * 15 * (1 - _insulation); };

        // Wind chill: convective cooling on exposed areas only.
        _target = _target - _windSpeed * 2 * (1 - _insulation);

        _emissivity = 0.95; // clothing surface (fabric)
        _tau = 60;          // human body: fast response
    } else {
        _isVehicle = _obj isKindOf "LandVehicle" || _obj isKindOf "Air" || _obj isKindOf "Ship";
        if (_isVehicle) then {
            // Metal body: strong solar absorption, low thermal mass.
            _emissivity = 0.9;
            _tau = 120;
            if (!_inShade) then { _target = _target + _solar * 0.7 * 15; };

            if (isEngineOn _obj) then {
                // Engine running: accumulate run time and warm the body.
                _engineRunTime = _engineRunTime + _dt;
                private _engineHeat = 40 * (1 - exp (-_engineRunTime / 300));
                _target = _target + _engineHeat;

                // Exhaust: hot within a minute; a small share of the
                // exhaust heat raises the vehicle's average signature.
                private _exhaustTemp = _airTemp + 200 * (1 - exp (-_engineRunTime / 60));
                _target = _target + (_exhaustTemp - _airTemp) * 0.05;
            } else {
                // Engine off: the accumulated run time decays with
                // tau = 300 s, so the body cools back toward ambient.
                _engineRunTime = _engineRunTime * exp (-_dt / 300);
            };
        } else {
            // Painted static weapon: paint lowers solar absorption.
            _emissivity = 0.92;
            _tau = 120;
            if (!_inShade) then { _target = _target + _solar * 0.6 * 15; };
        };

        // Convective cooling pulls the surface toward air temperature.
        _target = _target - _windSpeed * 2;
        _target = _target max _airTemp;
    };

    // Radiant temperature: lower emissivity radiates less heat.
    _target = _target - (1 - _emissivity) * 2;

    // Thermal inertia: exponential approach to the equilibrium target.
    _currentTemp = _currentTemp + (_target - _currentTemp) * (1 - exp (-_dt / _tau));

    // ─── Burning / incendiary damage ───────────────────────────────────
    // An object on fire burns at 600-800 C (combustion), saturating the
    // thermal signature regardless of ambient.  The engine signals fire
    // via damage: incendiary rounds and fire effects push damage toward
    // 1.0 while the object still exists (a destroyed wreck also smoulders
    // for a while).  Detect: damage >= 0.7 (heavy/fire damage) OR the
    // vehicle's fuel/engine hitpoints at critical damage (burning fuel).
    private _isBurning = false;
    if (damage _obj >= 0.7) then { _isBurning = true; };
    if (_obj isKindOf "AllVehicles") then {
        // getAllHitPointsDamage returns [names[], selections[], damages[]]
        // — three parallel arrays, NOT [name, selection, damage] triples.
        // Each _x is a STRING (the hitpoint name); the damage is at the
        // same index in the damages array.
        private _hpData = getAllHitPointsDamage _obj;
        if (count _hpData >= 3 && {count (_hpData select 0) > 0}) then {
            private _hpNames = _hpData select 0;
            private _hpDamages = _hpData select 2;
            for "_i" from 0 to (count _hpNames - 1) do {
                if ((_hpDamages select _i) >= 0.7) then {
                    private _hp = toLower (_hpNames select _i);
                    if (_hp find "fuel" >= 0 || _hp find "engine" >= 0) then {
                        _isBurning = true;
                    };
                };
            };
        };
    };
    if (_isBurning) then {
        // Combustion temperature: the surface reads near-saturated.
        // 600 C above ambient on the ~50 C heat scale = saturated.  The
        // current temp rises toward it with the object's inertia.
        _target = _airTemp + 600;
    };

    // Fog scatters IR: dense fog pulls the apparent temperature toward
    // ambient.  The physical temperature (and averages) stay unattenuated.
    private _reportedTemp = _currentTemp + (_airTemp - _currentTemp) * _fog * 0.5;

    _thermalState set [_objKey, [_currentTemp, _engineRunTime, _now, _acclimatisation, _obj]];
    _results pushBack [_obj, round (_reportedTemp * 10) / 10];

    if (_isInfantry) then {
        _infantrySum = _infantrySum + _currentTemp;
        _infantryCount = _infantryCount + 1;
    } else {
        if (_isVehicle) then {
            _vehicleSum = _vehicleSum + _currentTemp;
            _vehicleCount = _vehicleCount + 1;
        };
    };
} forEach _objects;

// ─── Conduction / radiant coupling between nearby objects ─────────────────
// A hot object (running engine, exhaust, fire) transfers heat to objects
// close to it: the radiator heats the air around the engine bay, a parked
// car beside a running one warms slowly, a burning vehicle heats
// everything within metres.  Real thermodynamics: heat flows from hot to
// cold, faster when the temperature difference is larger and the gap
// smaller.  The engine has no per-surface conduction model, so this is a
// proximity term on the per-object equilibrium: each object receives a
// small share of a nearby hotter object's surplus, scaled by 1/distance.
//
// One pass over the stored state: for each object with a hot neighbour
// (within 10 m, at least 5 C warmer), pull its temperature up a little.
// The effect is small per tick (heat takes time to transfer) and bounded
// so it cannot destabilise the solve.  Hot sources are gathered once.
private _hotSources = [];
{
    _x params ["_nKey", "_nVal"];
    if (count _nVal < 5) then { continue; };
    private _nObj = _nVal select 4;
    if (isNull _nObj || !alive _nObj) then { continue; };
    private _nTemp = _nVal select 0;
    if !(_nTemp isEqualType 0) then { continue; };
    _hotSources pushBack [_nKey, _nObj, _nTemp];
} forEach (keys _thermalState);

{
    _x params ["_oKey", "_oVal"];
    if (count _oVal < 5) then { continue; };
    private _oObj = _oVal select 4;
    if (isNull _oObj || !alive _oObj) then { continue; };
    private _oTemp = _oVal select 0;
    if !(_oTemp isEqualType 0) then { continue; };

    // Sum the coupling from hot neighbours.
    private _coupling = 0;
    {
        _x params ["_nKey", "_nObj", "_nTemp"];
        if (_nKey == _oKey) then { continue; };
        if (_nTemp <= _oTemp + 5) then { continue; };   // not hot enough
        private _d = _oObj distance _nObj;
        if (_d > 10) then { continue; };
        // Radiant transfer ~ (1/d^2) scaled: a hot neighbour 2 m away
        // with 40 C surplus contributes ~3 C; 8 m away ~0.2 C; 80 C
        // surplus at 3 m ~2.7 C.  The coupling only nudges, never
        // dominates (the surplus is spread over distance^2 and the
        // result is bounded).
        private _surplus = _nTemp - _oTemp;
        private _share = (_surplus * (0.3 / (_d * _d))) min 4;
        _coupling = _coupling + _share;
    } forEach _hotSources;

    // Apply: bounded to a few degrees per tick (heat transfer is slow),
    // then re-store.  The inertia next tick smooths it.
    if (_coupling > 0.05) then {
        _coupling = _coupling min 5;
        _oVal set [0, _oTemp + _coupling];
        _thermalState set [_oKey, _oVal];
    };
} forEach (keys _thermalState);

// ─── Stale entry cleanup ──────────────────────────────────────────────────
// Keys are strings; the object reference is stored as element 4 of the value.
{
    private _val = _thermalState getOrDefault [_x, []];
    if (count _val > 4) then {
        private _ref = _val select 4;
        if (isNull _ref || {!alive _ref}) then {
            _thermalState deleteAt _x;
        };
    };
} forEach (keys _thermalState);

missionNamespace setVariable [QGVAR(thermalState), _thermalState];

// ─── Summary averages ─────────────────────────────────────────────────────
private _avgVehicle = if (_vehicleCount > 0) then { _vehicleSum / _vehicleCount } else { _airTemp };
private _avgInfantry = if (_infantryCount > 0) then { _infantrySum / _infantryCount } else { _airTemp };

missionNamespace setVariable [QEGVAR(core,objectTemperatures), _results];
missionNamespace setVariable [QEGVAR(core,avgVehicleTemp), _avgVehicle];
missionNamespace setVariable [QEGVAR(core,avgInfantryTemp), _avgInfantry];
missionNamespace setVariable [QEGVAR(core,avgGroundTemp), _groundTemp];

private _logMsg = format ["thermal: air %1, ground %2, vehicle %3, infantry %4, objects %5", _airTemp, _groundTemp, _avgVehicle, _avgInfantry, count _results];
AEE_LOG_DEBUG(_logMsg);

_results
