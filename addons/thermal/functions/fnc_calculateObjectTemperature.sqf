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
    ["_maxObjects", 50, [0]],
    ["_dtOverride", -1, [0]]
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
// Real solar FLUX in W/m2 (issue #124 audit): the factor is
// sin(elevation) x cloud; the flux is that x 1000 W/m2 (ASTM G173).
private _solarFlux = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), _solar * 1000];
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
// Per-position ground solve (issue #124).  The old per-class gain table
// (a 5-15 C offset hack per surface type) and the manual wind/shade
// re-application are gone: the real solver does the full energy balance
// per material (asphalt absorbs far more than grass - alpha from the
// material registry), handles cloud via the flux, and adds thermal
// stamps.  The only thing kept here is the object's own inertia toward
// the ground it stands on (a vehicle on hot asphalt warms through its
// tyres - see _groundTau below).
private _centerASL = getPosASL _center;
private _groundTarget = [_centerASL] call FUNC(calculateGroundTemperature);

// Ground thermal inertia: exponential approach to the target.  The
// step is the wall-clock delta since the last tick, clamped so a long
// pause cannot teleport the temperature.
private _groundTau = 600;  // generic ground: slow (rock/sand); vegetation is 300 in the solver
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
    // Elapsed time since the last solve.  Real-time path: the env PFH runs
    // every 5 s, so dt is 5 s (clamped 30 s max for safety after long
    // pauses).  CALIBRATION path: _dtOverride (>= 0) simulates the real
    // elapsed time directly, so the 24 h sweep can step the clock by the
    // hour and still exercise the full exponential inertia curve (the
    // 30 s clamp would otherwise freeze the vehicle at its night temp).
    private _dt = if (_dtOverride >= 0) then {
        _dtOverride
    } else {
        if (_hasState) then { ((_now - (_state select 2)) max diag_deltaTime) min 30 } else { 0 }
    };

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

        // ─── Blood and body-state thermals (issue #124) ──────────────────
        // Real physiology drives the surface temperature a thermal imager
        // sees.  Three states, each with cited physics:
        //
        // 1. DEAD (not alive): metabolism stops (basal ~100 W gone).
        //    The body cools toward ambient by Newton's law of cooling
        //    with a long tau - forensic post-mortem cooling (Henssge
        //    nomogram, Marshall & Hoare 1962): a clothed body loses
        //    ~1 C/h initially, slowing as it approaches ambient.  The
        //    SURFACE (what FLIR sees) cools faster than the core but
        //    reads warm for hours.  tau 7200 s = ~1 C/h.
        // 2. DYING (alive, blood loss): hypovolaemic shock drives
        //    peripheral vasoconstriction - blood moves centrally, the
        //    skin/limb surface cools (classic cold-extremities sign).
        //    Metabolic heat and the surface base both scale down with
        //    blood volume (ACE ace_medical_bloodVolume, 6.0 L full).
        // 3. HEALTHY: normal metabolic heat from movement (below).
        private _isDead = !alive _obj;
        private _bloodVol = _obj getVariable ["ace_medical_bloodVolume", 6.0];
        if !(_bloodVol isEqualType 0) then { _bloodVol = 6.0; };
        private _bloodFrac = (_bloodVol max 0 min 6) / 6.0;  // 0..1
        // Shock threshold: below ~40% blood volume the circulation
        // fails (compensated -> decompensated shock, ATLS).
        private _shock = linearConversion [0.4, 0.0, _bloodFrac, 0, 1, true];

        if (_isDead) then {
            // No metabolism.  The corpse surface relaxes toward ambient
            // with forensic cooling (tau 7200 s ≈ 1 C/h - Henssge).
            _target = _airTemp;
            _tau = 7200;
            // Solar still warms the exposed surface (a corpse in sun
            // doesn't stay cold), scaled to the corpse's surface.
            if (!_inShade) then { _target = _target + ((1 - _insulation) * (([0.6, _solarFlux, 0.95, _airTemp, _windSpeed] call FUNC(solarElevation)))); };
        } else {
            // Metabolic heat from movement: idle 0, walk 20, run 60,
            // sprint 120 W - SCALED by blood fraction (a bleeding man
            // cannot generate full sprint heat) and suppressed entirely
            // by shock.
            private _vSpeed = abs speed _obj;
            private _metabolicHeat = switch (true) do {
                case (_vSpeed > 6):   { 120 };
                case (_vSpeed > 3):   {  60 };
                case (_vSpeed > 0.5): {  20 };
                default               {   0 };
            };
            _metabolicHeat = _metabolicHeat * _bloodFrac * (1 - _shock * 0.8);
            _target = _target + _metabolicHeat * 0.05;

            // The surface base erodes with shock: cold extremities as
            // blood moves centrally (ATLS shock physiology).
            _target = _target - _shock * 8;

            // Solar gain on exposed skin, scaled by the exposed fraction.
            if (!_inShade) then { _target = _target + ((1 - _insulation) * (([0.6, _solarFlux, 0.95, _airTemp, _windSpeed] call FUNC(solarElevation)))); };

            // Wind chill: convective cooling on exposed areas only.
            _target = _target - _windSpeed * 2 * (1 - _insulation);

            // Body response slows as circulation fails: a healthy man
            // responds in ~60 s, a shocked body in minutes.
            _tau = 60 + _shock * 300;
        };

        _emissivity = 0.95; // clothing surface (fabric)
    } else {
        _isVehicle = _obj isKindOf "LandVehicle" || _obj isKindOf "Air" || _obj isKindOf "Ship";
        if (_isVehicle) then {
            // Metal body: strong solar absorption, low thermal mass.
            _emissivity = 0.9;
            _tau = 120;
            if (!_inShade) then { _target = _target + ([0.7, _solarFlux, 0.9, _airTemp, _windSpeed] call FUNC(solarElevation)); };

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
            if (!_inShade) then { _target = _target + ([0.6, _solarFlux, 0.92, _airTemp, _windSpeed] call FUNC(solarElevation)); };
        };

        // Convective cooling pulls the surface toward air temperature.
        _target = _target - _windSpeed * 2;
        // Radiative-equilibrium floor (air - 5 C, not air): the OLD
        // `max _airTemp` erased the day-time solar gain whenever wind
        // cooling exceeded it (a sunlit vehicle read exactly air temp in
        // the 10-54 calibration sweep), and blocked real night cooling.
        _target = _target max (_airTemp - 5);
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

    // Ground thermal painting (issue #124): vehicles lay tyre/stamp
    // patches, a parked-then-driven vehicle leaves a cool shade patch,
    // soldiers leave boot-print heat.  Cheap - one contact stamp per
    // tracked object per tick, and the ground solve adds it back.
    _obj call FUNC(applyGroundContactStamps);

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

// ─── Radiant coupling between nearby objects (issue #124 audit) ───────────
// A hot object (running engine, exhaust, fire) transfers heat to objects
// close to it: the radiator heats the air around the engine bay, a parked
// car beside a running one warms slowly, a burning vehicle radiates
// enough to cook everything within metres.  Real heat flow is
// Stefan-Boltzmann radiant exchange to the fourth power (a fire at
// 600 C radiates ~100x more than a warm engine at 100 C), so the old
// linear `surplus / d^2` model under-radiated fires and over-coupled
// warm neighbours.
//
// One pass over the stored state: for each object with a hot neighbour
// (within 10 m, at least 5 C warmer), pull its temperature up by the
// radiant share.  The effect is bounded so it cannot destabilise the
// solve.  Hot sources are gathered once.
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

        // REAL radiant exchange (issue #124 audit): the old linear
        // `_surplus * (0.3 / d^2)` was wrong twice.  Radiant flux is
        // Stefan-Boltzmann to the FOURTH power:
        //   q = F_ij * eps * sigma * (T1^4 - T2^4)     [W/m2]
        // and the receiving surface's temperature elevation is q / h.
        // A fire (600 C) radiates ~100x more than a warm engine (100 C)
        // and, being a large-area emitter, does NOT fall off as 1/d^2
        // over the 10 m reach - it cooks everything nearby.  The view
        // factor F captures that: a burning vehicle is a near-blackbody
        // hemisphere (F ~0.5), a warm engine a modest radiator (F ~0.05).
        private _hotK = _nTemp + 273.15;
        private _coldK = _oTemp + 273.15;
        private _fView = [0.05, 0.5] select (_nTemp > 300);
        private _qRad = _fView * 0.9 * 5.670374419e-8 * ((_hotK ^ 4) - (_coldK ^ 4));
        private _share = _qRad / 10;   // h ~10 W/m2K (windy ambient)
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
