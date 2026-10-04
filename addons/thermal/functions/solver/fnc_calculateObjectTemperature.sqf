#include "..\..\script_component.hpp"

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

private _perfT0 = diag_tickTime;
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
private _solar = [overcast] call EFUNC(environmental,calculateSolarRadiation);
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
private _thermalState = missionNamespace getVariable [QGVAR(thermalState), -1];
if (_thermalState isEqualType 0) then {
    _thermalState = createHashMap;
    missionNamespace setVariable [QGVAR(thermalState), _thermalState];
};
private _now = diag_tickTime;

// ─── Scan interval gate ───────────────────────────────────────────────────
// This is the most expensive call in the environment tick: a nearestObjects
// query, up to fifty lineIntersectsSurfaces raycasts, and around five
// hundred Newton iterations, on EVERY machine whenever the tick fires.
//
// The scan does not need the tick rate. The surface temperatures it feeds
// run on time constants of 600 s (ground), 1800 s (acclimatisation) and
// about 7200 s (a vehicle), and the solver already integrates an arbitrary
// step through exp(-dt/tau). A 30 s step differs from a 5 s step by 0.3%
// of the approach to equilibrium, which is well inside the model's own
// uncertainty, so the scan runs on its own clock and the tick calls it
// cheaply.
//
// Set the interval to 0 to scan every tick, which restores the old
// behaviour for a calibration sweep.
private _scanInterval = missionNamespace getVariable [QGVAR(objectScanInterval), 30];
if !(_scanInterval isEqualType 0) then { _scanInterval = 30; };
// The early exit must be a SINGLE top-level if-exitWith, the same shape as the
// isNull _center guard above.  MEASURED DEFECT: with the exitWith nested inside
// the then-block of the interval test, the scan ran on EVERY 5 s environment
// tick (RPT scan log at 9:28:03/:08/:13/:18 and every older run too), while a
// working 30 s throttle averages ~2-3 ms.  It read 10-14 ms/call sustained.
private _lastScan = missionNamespace getVariable [QGVAR(objectScanLast), -1e9];
if ((_scanInterval > 0) && {(_now - _lastScan) < _scanInterval}) exitWith {
    // Not due. Publish the cached summary so a consumer still reads a
    // value rather than nothing.
    missionNamespace getVariable [QGVAR(objectTemperatureSummary), []]
};
missionNamespace setVariable [QGVAR(objectScanLast), _now];

// ─── Ground temperature ───────────────────────────────────────────────────
// The ground temperature comes from FUNC(calculateGroundTemperature), which
// delegates to the per-position node stack and carries its own thermal
// memory.  A second exponential filter here double-integrated it, and its
// tau was a chosen 600 s; both are removed.
private _centerASL = getPosASL _center;
private _groundTarget = [_centerASL] call FUNC(calculateGroundTemperature);
private _groundTemp = _groundTarget;
_thermalState set ["ground", [_groundTemp, _now]];

// ─── Loop-invariant evaporation terms ─────────────────────────────────────
// These depend only on wind, air temperature, humidity and rain, none of
// which change during one scan, yet they were recomputed for EVERY object.
// _eAir carries an exp() and the humidity is a missionNamespace read.
private _hConv = 5.7 + 3.8 * (_windSpeed max 0);   // McAdams 1954
private _rhFrac = (missionNamespace getVariable [QEGVAR(core,currentHumidity), 50]) / 100;
if !(_rhFrac isEqualType 0) then { _rhFrac = 0.5; };
private _rv = 461.5;                  // water-vapour gas constant, J/kgK
private _lv = 2.45e6;                 // latent heat of vaporisation, J/kg
private _hM = _hConv / (1.2 * 1005);  // kg/(m2 s)
private _eAir = 611.2 * exp (17.67 * _airTemp / (_airTemp + 243.5)) * (_rhFrac max 0 min 1);
private _rhoVAir = _eAir / (_rv * (_airTemp + 273.15));
private _wet = rain > 0.02;

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
        //    Oxidative heat is delivery-limited and the surface base erodes;
        //    both come from the shared oxygen model in the alive branch.
        // 3. HEALTHY: normal metabolic heat from movement (below).
        private _isDead = !alive _obj;

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
            // sprint 120 W - SCALED by the fraction of oxidative metabolism
            // the circulation can still supply.
            private _vSpeed = abs speed _obj;
            private _metabolicHeat = switch (true) do {
                case (_vSpeed > 6):   { 120 };
                case (_vSpeed > 3):   {  60 };
                case (_vSpeed > 0.5): {  20 };
                default               {   0 };
            };
            // Oxygen delivery (issue #196): one blood model shared with
            // fnc_applySelectionThermal.  The metabolic fraction is
            // delivery-limited; the perfusion index is the volume axis.
            private _basalHeat = 58.2 * 1.8258;
            private _ox = [_obj, _basalHeat + _metabolicHeat, 1.8258] call EFUNC(physiology,calculateOxygenDelivery);
            _metabolicHeat = _metabolicHeat * (_ox select 6);
            private _shock = 1 - (_ox select 10);
            _target = _target + _metabolicHeat * 0.05;
            // Non-oxidative heat (DERIVED): the anaerobic deficit still
            // produces heat, which the oxidative fraction does not carry.
            // Basis: glycolysis gives 123.6 kJ per mol glucose to 2 lactate
            // over 6 mol O2 = 134.4 L, so 0.92 kJ/L; Minakami & de Verdier
            // 1976 (PMID 7451), 71 kJ per mol lactate, gives 1.06 kJ/L.
            // Use 1.0 J per mL O2 (range 0.9-1.1): the term is
            // deficit[mL O2/min] * 1.0 / 60 in W.  That is about 5 percent
            // of the 20.1 J/mL oxidative equivalent, so it is small.
            private _extraHeat = (_ox select 7) * 1.0 / 60;
            _target = _target + _extraHeat * 0.05;

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

        // Clothing surface is fabric; the display reads the selection
        // emissivity from the material registry, not from this branch.
    } else {
        _isVehicle = _obj isKindOf "LandVehicle" || _obj isKindOf "Air" || _obj isKindOf "Ship";
        private _matClass = "concrete";                 // painted static weapon
        if (_isVehicle) then { _matClass = "metal"; };
        // CACHED.  The material registry is static, so this lookup is computed
        // once per material class instead of once per object per tick.
        private _matCache = missionNamespace getVariable [QGVAR(objMatCache), -1];
        if (_matCache isEqualType 0) then {
            _matCache = createHashMap;
            missionNamespace setVariable [QGVAR(objMatCache), _matCache];
        };
        private _mat = _matCache getOrDefault [_matClass, []];
        if (_mat isEqualTo []) then {
            _mat = [_matClass] call FUNC(getMaterialThermal);
            _matCache set [_matClass, _mat];
            missionNamespace setVariable [QGVAR(objMatCache), _matCache];
        };
        _mat params ["_eps", "_alpha", "_rhoM", "_cpM", "_kM", "_phiM"];

        // Real dimensions: L_c = V/A sets the lumped-capacitance length and
        // the surface area (Incropera Ch. 5).  boundingBoxReal is the true
        // model size.  CACHED BY TYPE: it is an engine call and the model
        // dimensions cannot change at runtime, so the derived area and lumped
        // length are computed once per object type, not per object per tick.
        private _geoCache = missionNamespace getVariable [QGVAR(objGeoCache), -1];
        if (_geoCache isEqualType 0) then {
            _geoCache = createHashMap;
            missionNamespace setVariable [QGVAR(objGeoCache), _geoCache];
        };
        private _typeKey = typeOf _obj;
        private _geo = _geoCache getOrDefault [_typeKey, []];
        if (_geo isEqualTo []) then {
            private _bb = boundingBoxReal _obj;
            private _lx = 1; private _ly = 1; private _lz = 1;
            if ((_bb isEqualType []) && {(count _bb) == 2}) then {
                private _bMin = _bb select 0;
                private _bMax = _bb select 1;
                _lx = (abs ((_bMax select 0) - (_bMin select 0))) max 0.1;
                _ly = (abs ((_bMax select 1) - (_bMin select 1))) max 0.1;
                _lz = (abs ((_bMax select 2) - (_bMin select 2))) max 0.1;
            };
            private _areaC = (2 * ((_lx * _ly) + (_lx * _lz) + (_ly * _lz))) max 0.1;
            private _lCapC = (((_lx * _ly * _lz) max 0.01) / _areaC) max 1e-4;
            _geo = [_areaC, _lCapC];
            _geoCache set [_typeKey, _geo];
            missionNamespace setVariable [QGVAR(objGeoCache), _geoCache];
        };
        private _areaObj = _geo select 0;
        private _lCap = _geo select 1;

        // Lumped-capacitance time constant (Incropera Ch. 5): tau = m*cp/(h*A).
        private _massObj = (getMass _obj) max 1;
        _tau = (_massObj * _cpM) / ((_hConv * _areaObj) max 1e-3);

        // Longwave is exchanged against the MEAN RADIANT TEMPERATURE
        // (ISO 7726: ground + Swinbank sky + neighbours), not the air, so a
        // clear calm night cools below air - the effect the old air-5 floor
        // deleted.
        private _mrtK = ([getPosASL _obj, 0.5] call FUNC(calculateMRT)) + 273.15;
        private _sigmaB = 5.670374419e-8;

        // Internal generation as a surface flux.  A running engine's
        // thermostat holds the body near the coolant setpoint, so the flux it
        // rejects is h*(T_op - Ta).  The exhaust gas temperature is real
        // (the repo's own exhaust tier table; Heywood 1988).
        //
        // No published source defines a body-area fraction at exhaust-port
        // gas temperature.  _exhFrac is an AEE lumped calibration: the
        // exhaust contributes about 5 percent of the rejected flux.  The
        // 480 C value is the gas INSIDE the pipe at the port (Heywood 1988).
        // The pipe skin downstream is cooler, so this fraction partly
        // compensates for using a gas temperature as a surface temperature.
        // A maintainer must read it as a calibration, not a measured area.
        //
        // Future option, not implemented here: model the exhaust as its own
        // surface of area pi*D*L at a cooler skin temperature, exchanging
        // with the body by radiation view factor and convection.  The
        // SAE 2016-01-0280 method gives the transient exhaust-surface
        // result; SAE 2008-01-1819 gives the conjugate plus radiation path
        // to the underbody.  The behaviour below is unchanged.
        private _qInt = 0;
        if (_isVehicle && {isEngineOn _obj}) then {
            _engineRunTime = _engineRunTime + _dt;
            private _tOp = 90;               // thermostat-open coolant temp, C
            private _tExh = 480;             // exhaust gas temp at the port, C
            private _exhFrac = 0.05;         // AEE lumped calibration
            _qInt = ((1 - _exhFrac) * ((_tOp max _airTemp) - _airTemp) + _exhFrac * ((_tExh max _airTemp) - _airTemp)) * _hConv;
        } else {
            _engineRunTime = _engineRunTime * exp (-_dt / _tau);
        };

        // Conduction to the ground the object stands on (series path through
        // its own material over L_c) - the old solve had no ground coupling.
        // HOISTED: identical call and argument to the pre-loop _groundTarget.
        // It was a full ground solve per object (surfaceType, the 4-layer node
        // stack, frost, a shadow raycast) repeated for one value already in
        // hand.
        private _tGround = _groundTarget;
        private _uGround = (_kM / _lCap) max 0;

        private _qSolar = _alpha * (_solarFlux max 0);
        if (_inShade) then { _qSolar = 0; };

        // Evaporative loss only when the surface is wet (rain).  Mass-transfer
        // coefficient from the heat-mass analogy (Incropera Ch. 6):
        // h_m = h_c/(rho*cp*Le^(2/3)), Le = 1 for air-water vapour.
        // (Terms hoisted before the scan: loop-invariant.)

        // Steady surface balance, Newton-solved:
        //   qSolar + qInt = h*(Ts-Ta) + eps*sigma*(Ts^4-MRT^4)
        //                   + U_g*(Ts-Tg) + qEvap(Ts)
        private _tsK = _airTemp + 273.16;
        for "_iter" from 1 to 12 do {
            private _tsC = _tsK - 273.15;
            private _qEvap = 0;
            if (_wet && (_tsC > 0)) then {
                private _rhoVsat = (611.2 * exp (17.67 * _tsC / (_tsC + 243.5))) / (_rv * _tsK);
                _qEvap = _hM * _lv * ((_rhoVsat - _rhoVAir) max 0);
            };
            private _res = _qSolar + _qInt
                - _hConv * (_tsC - _airTemp)
                - _eps * _sigmaB * ((_tsK ^ 4) - (_mrtK ^ 4))
                - _uGround * (_tsC - _tGround)
                - _qEvap;
            private _deriv = -(_hConv + (4 * _eps * _sigmaB * (_tsK ^ 3)) + _uGround);
            if (_deriv == 0) exitWith {};
            _tsK = _tsK - (_res / _deriv);
        };
        _target = _tsK - 273.15;
    };

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

private _scanMs = round ((diag_tickTime - _perfT0) * 1000);
// int %9 is the RESOLVED scan interval.  The 09:27:28 RPT proved the scan ran
// every 5 s while the interval should be 30; logging the resolved value tells
// the next run apart the two possible causes (gate semantics vs interval 0).
private _logMsg = format ["thermal: air %1, ground %2, vehicle %3, infantry %4, objects %5 | scan %6 ms | vehicles %7 | humans %8 | int %9",
    _airTemp, _groundTemp, _avgVehicle, _avgInfantry, count _results, _scanMs, _vehicleCount, _infantryCount,
    _scanInterval];
AEE_LOG_DEBUG(_logMsg);

// Cache the result so a tick inside the scan interval returns the last
// computed set rather than nothing. The published summary state above is
// already current, because it was written on the scan that produced it.
missionNamespace setVariable [QGVAR(objectTemperatureSummary), _results];

_results
