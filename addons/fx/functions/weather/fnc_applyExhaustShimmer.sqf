#include "..\..\script_component.hpp"

/*
Physics-driven exhaust heat-shimmer renderer.

A hot exhaust plume is less dense than the air around it, so its refractive
index is lower (Gladstone-Dale), and the density step bends light.  This
function draws that step as a vanilla refractive billboard attached to a
vehicle's exhaust, and it drives the billboard from the real refractive
contrast that fnc_calculateThermalRefraction returns.

SPRITE SIZE IS AT TRUE PHYSICAL SCALE, AND NO VISIBILITY SCALE FACTOR IS
USED BECAUSE NONE IS NEEDED.  The plume depth sets the sprite size in
metres, and the engine projects metres to pixels through the camera.  At
1080p with a 60 degree horizontal field of view the focal length in pixels
is 1662.8: focal_px = (1920 / 2) / tan(60 / 2 degrees).  A sprite of size S
metres at range R metres is S * 1662.8 / R pixels:

  a 0.5 m plume is 17 px at 50 m and 8 px at 100 m
  a 0.8 m plume is 27 px at 50 m and 13 px at 100 m
  a 2.0 m plume is 67 px at 50 m and 33 px at 100 m
  a 2.5 m plume is 83 px at 50 m and 42 px at 100 m
  for contrast, a 5.56 mm object is 0.18 px at 50 m

A plume is metres across, so it is visible without exaggeration, unlike a
bullet.  The absence of a fudge constant is the finding, not an omission.

THE POWER RAMP DRIVES THE PLUME SIZE, NOT ALPHA, AND THE ARITHMETIC SETTLES
IT.  The refractive contrast is a weak function of gas temperature.  At an
ambient of 15 C a 400 C gas gives a contrast magnitude of 1.58, a 600 C gas
gives 1.85, a 900 C gas gives 2.09, and a 1200 C gas gives 2.23.  That is a
factor of 1.4 across the whole range.  The plume depth runs 0.35 m to 2.5 m,
a factor of 7.  So the power ramp drives the plume depth, and the contrast
stays on the real gas-temperature curve.  A renderer that ramps alpha with
power is wrong, because alpha is not a physical quantity and the contrast
barely moves.  The renderer calls fnc_calculateExhaustPlume for the depth
and fnc_calculateThermalRefraction for the contrast, and power never reaches
the alpha expression.

ALPHA IS THE ONLY FREE LEVER FOR VISIBILITY.  Fill rate is sprite count
times sprite area and never alpha, so visibility is bought with alpha alone.
The refract billboard samples the framebuffer and is among the most
expensive particle types, so the emitter count and the sprite size are the
budget.

OVERDRAW SCALES WITH THE PLUME AREA.  The repository measured 190 square
metres of overdraw as acceptable and 642 square metres as a stutter on
27 Sep 2026.  The previous renderer held a fixed 12 live sprites per source,
so at its old 2.0 m maximum depth the worst case was 3 sources * 12 live *
2.0^2 = 144 square metres, below the 190.  The user chose a 2.5 m maximum,
which breaks that fixed-count bound: 3 * 12 * 2.5^2 = 225 square metres,
ABOVE the measured acceptable figure.  So the live count derives from the
plume area.  The count is floor(_OVERDRAW_BUDGET / (_MAX_SOURCES *
depth^2)), clamped between the _MIN_LIVE floor and the _MAX_LIVE ceiling.
At 0.35 m the count is the 12 ceiling, and the overdraw is 3 * 12 * 0.35^2
= 4.4 square metres.  At 2.5 m the count is floor(190 / (3 * 6.25)) = 10,
and the overdraw is 3 * 10 * 2.5^2 = 187.5 square metres.  The bound is
tight and reaches 190 square metres exactly at the depth where the count
steps down, which is 2.297 m and 2.399 m, so the product never exceeds 190.
The budget constant is the measured 190 and not a guess.  The floor keeps a
large plume visible, and the ceiling keeps a tiny plume from becoming a
fill-rate problem.  The per-source drop interval and the lifetime derive
from the live count, so the particle lifecycle stays consistent.  The
lifetime sits in index 4 of the particle array, per
docs/wiki/research/particle-array-spec.md line 32 and vanilla
muzzle/rockettrail.sqf, and the derived drop interval is the only other term.

PER-CLASS PLUME PROFILES, DECLARED AS DEFAULTS AND NOT AS MEASUREMENTS.  The
repository holds no measured exhaust data, so these endpoints are declared
defaults.  fnc_calculateExhaustPlume interpolates between the idle and full
endpoints on the engine power fraction.  The tiers are:
  - land vehicle, diesel: idle 300 C / 0.35 m, full 480 C / 0.60 m
  - helicopter, turboshaft: idle 420 C / 0.35 m, full 600 C / 1.00 m
  - fixed wing, dry turbofan: idle 480 C / 0.40 m, full 750 C / 1.50 m
  - jet with afterburner: idle 550 C / 0.50 m, full 1200 C / 2.50 m

THE CLASS TIER IS SELECTED PER VEHICLE, AND EVERY TIER IS REACHABLE.  A
per-vehicle tier override named aee_exhaustTier wins outright.  Otherwise a
helicopter takes the turboshaft row, a vehicle whose aee_exhaustAfterburner
variable holds a truthy value takes the afterburner row, a plane takes the
dry turbofan row, and everything else takes the land diesel row.  The
afterburner row is not selected by kindOf, because no verified config key
distinguishes an afterburning jet from a dry one, and a class-name guess
list would be an invented fact.  A mission or mod sets aee_exhaustAfterburner
on the vehicle.  The helicopter branch exists because vanilla Air has two
roots: Helicopter: Air and Plane: Air, both verified in the vanilla air_f
and air_f_beta configs.  A helicopter is not a Plane, so the previous single
isKindOf "Plane" branch silently gave every helicopter the fixed-wing row.

POWER RESOLUTION, IN THE ORDER THE USER CHOSE.  The real reader is the
RotorLib real-time data interface: collectiveRTD for a helicopter and
throttleRTD for fixed wing, both unary with a scalar return.  The RTD group
reports meaningful values only when the advanced helicopter flight model is
on, which the code tests with difficultyEnabledRTD.  When the model is off
the RTD numbers are not evidence of engine power, so the code falls through
to the next source rather than draw a plume from a meaningless zero.  A
land vehicle has no RTD throttle and never reads.  The power fraction
resolves in this order:
  1. a published per-vehicle value named aee_enginePowerFraction, in 0..1,
     which a mission or a mod sets.  This is the path a mission uses
  2. the real reader: collectiveRTD for a helicopter and throttleRTD for
     fixed wing, behind the difficultyEnabledRTD guard, with a type check
     on the return.  A helicopter uses collective and a plane uses throttle
  3. the DERIVED ground-vehicle term for a LandVehicle, from the published
     traction force and the acceleration between ticks.  See below
  4. otherwise the declared idle fraction, so a parked aircraft and a land
     vehicle at rest still show a small plume rather than nothing
The reader is gated on the flight model and is unavailable when it is off.

NO ROAD-THROTTLE READER EXISTS IN THE ENGINE, SO THE LAND TERM IS DERIVED
AND NOT MEASURED.  collectiveRTD is rotary and throttleRTD is fixed wing, so
a LandVehicle selects neither string and its load would otherwise stay at
the declared idle for every speed.  getInfo is absent from the client
binary, and the AEE mobility model carries no engine-load reader either.
The load therefore comes from the physical power balance in
fnc_calculateEngineLoad: the tractive demand plus the power to accelerate
the inertia.  The object work stays here.  This function reads the
published aee_mobility_tractionForce, reads the mass with getMass, and
differences the vehicle velocity between ticks for the acceleration.  The
acceleration is smoothed with the declared time constant _ACCEL_TAU,
because a velocity difference is noisy.  A STATIONARY VEHICLE AT HIGH RPM
CANNOT BE DISTINGUISHED FROM ONE AT IDLE, because the engine does not
publish rpm for a road vehicle, so the kernel floors the result at the idle
fraction.  That is a LIMIT OF THE ENGINE, not an approximation this
function chose.  The published aee_mobility_tractionForce belongs to the
local player's vehicle; a nearby candidate reuses it, which is a stated
approximation.  The rated power is read from an optional per-vehicle
aee_engineRatedPowerW, else it is the kernel default of 150000 W, a
declared default and not a measurement.

THE READER IS COMPILED AT RUN TIME, BECAUSE THE ENGINE COMMAND SET DIFFERS
BETWEEN BUILDS.  The fixed-wing reader throttleRTD is present in the game
client but absent from the harness dedicated-server binary, where the bare
token is a parse error.  This function is compiled on every machine, so a
direct reference would stop the addon loading on that server.  The reader
string is compiled when the flight model is on and the reader is reached,
which only happens on a client.  collectiveRTD IS present in the harness
server binary, but both readers take the same path so one binary change
cannot break the file.  The RTD path is a game-only path; a server never
reaches it.

The mobility value aee_mobility_enginePowerModifier is NOT used, because it
is an air-density derate and not an engine power state.

MEASURED PER-VEHICLE VALUES WIN OVER THE CLASS ROW.  The vehicle variables
aee_exhaustGasTempC (Celsius) and aee_exhaustPlumeM (metres) are read and
they override the kernel output, because a measured value beats a declared
one.

EXHAUST GAS TEMPERATURE IS NOT REACHABLE FROM THE THERMAL SOLVER.  The AEE
thermal solver publishes aee_core_objectTemperatures as [object, surface
temperature] pairs and aee_thermal_selTemperature as a map of per-selection
SURFACE temperatures.  Neither is an exhaust GAS temperature.  So no
reachable per-object exhaust gas temperature exists, and the class row is
used instead, with the per-vehicle override for a measured value.  This is
stated rather than hidden.

GATED ON currentVisionMode.  A non-zero vision mode means the engine draws
its own NVG or thermal image, and a refractive plume has no place on top of
it.  The gate deletes every source, because a #particlesource keeps
emitting when it is only hidden.  The PHYSICS stays ungated: the contrast is
computed and published on every tick, even in a sensor mode, because it is a
property of the air and not of the display.  Only the render is gated.

CLIENT ONLY.  The function refuses without an interface, so a dedicated
server creates nothing and renders nothing.

Arguments: none.  Reads the local player through CBA_fnc_currentUnit.

Returns: nothing.  Side effects: up to _MAX_SOURCES particle sources, one
record on aee_fx_exhaustSources, and the published contrast
aee_fx_exhaustRefraction.
*/

if (!hasInterface) exitWith {};
if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};
private _veh = vehicle _player;
if (cameraOn != _player && cameraOn != _veh) exitWith {};

// Budget constants.  See the header for the overdraw arithmetic.
private _LIFETIME = 1.2;
private _MAX_SOURCES = 3;
private _OVERDRAW_BUDGET = 190;
private _MAX_LIVE = 12;
private _MIN_LIVE = 4;
private _MIN_CONTRAST = 0.1;
private _PLUME_RANGE = 250;
private _IDLE_POWER = 0.05;
private _ACCEL_TAU = 5.0;

// ─── Class tier table ──────────────────────────────────────────────────────
// One row per engine class: [idleTempC, fullTempC, idleDepthM, fullDepthM].
// Declared defaults, not measurements.  See the header.
private _TIERS = createHashMapFromArray [
    ["land", [300, 480, 0.35, 0.60]],
    ["heli", [420, 600, 0.35, 1.00]],
    ["jet", [480, 750, 0.40, 1.50]],
    ["ab", [550, 1200, 0.50, 2.50]]
];

// ─── Tier selection ────────────────────────────────────────────────────────
// Each branch covers a case the others cannot.  See the header.
private _selectTier = {
    params ["_veh", "_tiers"];
    private _tier = "";
    private _override = _veh getVariable ["aee_exhaustTier", ""];
    if (_override isEqualType "") then {
        private _row = _tiers getOrDefault [_override, false];
        if (_row isEqualType []) then { _tier = _override; };
    };
    if (_tier == "") then {
        if (_veh isKindOf "Helicopter") then {
            _tier = "heli";
        } else {
            if (_veh getVariable ["aee_exhaustAfterburner", false]) then {
                _tier = "ab";
            } else {
                if (_veh isKindOf "Plane") then {
                    _tier = "jet";
                } else {
                    _tier = "land";
                };
            };
        };
    };
    _tier
};

// ─── Derived ground-vehicle load ───────────────────────────────────────────
// A road vehicle has no readable throttle, so the load is derived from the
// published traction force and the acceleration between ticks.  The object
// work lives here and the kernel is pure arithmetic.  The acceleration comes
// from the vehicle's own velocity difference, held per vehicle, and it is
// smoothed with _ACCEL_TAU because a difference is noisy.  A stationary
// engine reaches only the idle floor, because the engine publishes no rpm.
private _deriveGroundPower = {
    params ["_veh", "_idlePower", "_accelTau"];
    private _now = diag_tickTime;
    private _speed = vectorMagnitude (velocity _veh);
    private _prevSpeed = _veh getVariable ["aee_exhaustPrevSpeed", _speed];
    private _prevTime = _veh getVariable ["aee_exhaustPrevTime", _now];
    private _smooth = _veh getVariable ["aee_exhaustSmoothAccel", 0];
    if !(_prevSpeed isEqualType 0) then { _prevSpeed = _speed; };
    if !(_prevTime isEqualType 0) then { _prevTime = _now; };
    if !(_smooth isEqualType 0) then { _smooth = 0; };
    private _dt = _now - _prevTime;
    if (_dt > 0) then {
        private _raw = (_speed - _prevSpeed) / _dt;
        _smooth = _smooth + ((_raw - _smooth) * (_dt / (_accelTau + _dt)));
    };
    _veh setVariable ["aee_exhaustPrevSpeed", _speed];
    _veh setVariable ["aee_exhaustPrevTime", _now];
    _veh setVariable ["aee_exhaustSmoothAccel", _smooth];

    private _force = missionNamespace getVariable [QEGVAR(mobility,tractionForce), 0];
    if !(_force isEqualType 0) then { _force = 0; };
    private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
    if !(_rho isEqualType 0) then { _rho = 1.225; };
    private _rated = _veh getVariable ["aee_engineRatedPowerW", 150000];
    if !(_rated isEqualType 0) then { _rated = 150000; };

    [_force, _speed, getMass _veh, _smooth, _rated, _idlePower, 0, _rho] call EFUNC(mobility,calculateEngineLoad)
};

// ─── Power resolution ──────────────────────────────────────────────────────
// A published value wins, then the real reader when the flight model is on,
// then the derived ground term, then the declared idle.  A missing compile
// or a bad return shape falls through.  See the header.
private _resolvePower = {
    params ["_veh", "_idlePower", "_accelTau"];
    private _power = -1;
    private _published = _veh getVariable ["aee_enginePowerFraction", -1];
    if (_published isEqualType 0) then {
        if (_published >= 0) then { _power = _published min 1; };
    };
    if (_power < 0) then {
        if (difficultyEnabledRTD) then {
            private _reader = "";
            if (_veh isKindOf "Helicopter") then {
                _reader = "collectiveRTD _this";
            } else {
                if (_veh isKindOf "Plane") then {
                    _reader = "throttleRTD _this";
                };
            };
            if (_reader != "") then {
                private _code = compile _reader;
                if (!isNil "_code") then {
                    private _raw = _veh call _code;
                    if (_raw isEqualType 0) then {
                        private _value = parseNumber (str _raw);
                        if (_value > 0) then { _power = _value min 1; };
                    };
                };
            };
        };
    };
    if (_power < 0) then {
        // A ground vehicle falls through the air reader, so the derived
        // branch is gated explicitly on the land root.  See the header.
        if (_veh isKindOf "LandVehicle") then {
            private _derived = [_veh, _idlePower, _accelTau] call _deriveGroundPower;
            if (_derived >= 0) then { _power = _derived; };
        };
    };
    if (_power < 0) then { _power = _idlePower; };
    _power
};

// ─── Live sprite count from the plume area ─────────────────────────────────
// Keep sources * live * depth^2 at or below the measured overdraw budget.
// See the header for the arithmetic at both ends of the size range.
private _liveCount = {
    params ["_depth", "_budget", "_sources", "_maxLive", "_minLive"];
    private _allowed = _budget / (_sources * _depth * _depth);
    ((floor _allowed) min _maxLive) max _minLive
};

// ─── Physics (ungated) ─────────────────────────────────────────────────────
// The contrast is a property of the air, so it is computed even in a sensor
// mode.  Only the render below is gated.  The published store is the
// strongest drawn contrast, decayed by half each tick so a plume that leaves
// the plan fades instead of snapping to zero; the read of the previous value
// is that decay.
private _env = call EFUNC(ballistics,getEnvironmentState);
private _airC = _env select 0;
private _rhoRel = _env select 2;

private _candidates = [];
private _own = vehicle _player;
if (_own != _player && alive _own && canMove _own && isEngineOn _own) then {
    _candidates pushBack _own;
};

if (count _candidates < _MAX_SOURCES) then {
    private _near = nearestObjects [_player, ["Air", "LandVehicle", "Ship"], _PLUME_RANGE];
    {
        if (count _candidates >= _MAX_SOURCES) exitWith {};
        if (!alive _x) then { continue; };
        if (!canMove _x) then { continue; };
        if (!isEngineOn _x) then { continue; };
        if (_x in _candidates) then { continue; };
        _candidates pushBack _x;
    } forEach _near;
};

private _plan = [];
private _prevMag = missionNamespace getVariable [QGVAR(exhaustRefraction), 0];
if !(_prevMag isEqualType 0) then { _prevMag = 0; };
private _maxMag = _prevMag * 0.5;
{
    private _cand = _x;
    private _tier = [_cand, _TIERS] call _selectTier;
    private _row = _TIERS getOrDefault [_tier, _TIERS get "land"];
    _row params ["_idleT", "_fullT", "_idleD", "_fullD"];

    // The power fraction drives the plume size, not the alpha.
    private _power = [_cand, _IDLE_POWER, _ACCEL_TAU] call _resolvePower;
    private _profile = [_power, _idleT, _fullT, _idleD, _fullD] call EFUNC(mobility,calculateExhaustPlume);
    private _gasC = _profile select 0;
    private _depth = _profile select 1;

    // A measured per-vehicle value wins over the declared class row.
    private _gasOverride = _cand getVariable ["aee_exhaustGasTempC", -1];
    if (_gasOverride isEqualType 0 && _gasOverride > 0) then { _gasC = _gasOverride; };
    private _depthOverride = _cand getVariable ["aee_exhaustPlumeM", -1];
    if (_depthOverride isEqualType 0 && _depthOverride > 0) then { _depth = _depthOverride; };

    private _contrast = [_gasC, _airC, _rhoRel] call EFUNC(mobility,calculateThermalRefraction);
    private _mag = abs _contrast;
    if (_mag > _maxMag) then { _maxMag = _mag; };

    if (_mag >= _MIN_CONTRAST) then {
        _plan pushBack createHashMapFromArray [
            ["veh", _cand],
            ["depth", _depth],
            ["mag", _mag]
        ];
    };
} forEach _candidates;

missionNamespace setVariable [QGVAR(exhaustRefraction), _maxMag];

// ─── Render gate ───────────────────────────────────────────────────────────
// A sensor image is the engine's own.  Delete the sources rather than fade
// them, because a particle source keeps emitting while it is hidden.
private _visionMode = currentVisionMode _player;
private _records = missionNamespace getVariable [QGVAR(exhaustSources), []];
if (_visionMode != 0) exitWith {
    {
        private _src = _x getOrDefault ["source", objNull];
        if (!isNull _src) then { deleteVehicle _src; };
    } forEach _records;
    missionNamespace setVariable [QGVAR(exhaustSources), []];
};

private _alphaMax = missionNamespace getVariable [QGVAR(exhaustShimmerAlpha), 0.15];
if !(_alphaMax isEqualType 0) then { _alphaMax = 0.15; };

// The one place the shared particle parameters live, so create and update
// cannot drift apart.  Index 4 is the lifetime.
private _applyParams = {
    params ["_source", "_depth", "_alpha", "_lifetime", "_dropInterval"];
    _source setParticleParams [
        ["\A3\data_f\ParticleEffects\Universal\refract", 1, 0, 1, 0],
        "",
        "Billboard",
        1,
        _lifetime,
        [0, 0, 0],
        [0, 0.4, 0.9],
        0,
        1.0,
        0.05,
        0,
        [_depth, _depth],
        [[1, 1, 1, 0], [1, 1, 1, _alpha], [1, 1, 1, 0]],
        [1000],
        1,
        0.5,
        "",
        "",
        _source,
        -1,
        false,
        -1
    ];
    _source setParticleRandom [0, [_depth, _depth, 0], [0, 0, 0], 0, 0, [0, 0, 0, 0], 0, 0];
    _source setDropInterval _dropInterval;
};

// The exhaust memory points vary by model.  The first that resolves is used;
// the rear-upper fallback is a declared default, not a claimed memory point.
private _exhaustOffset = {
    params ["_target"];
    private _offset = [0, 0, 0];
    {
        private _p = _target selectionPosition _x;
        if (vectorMagnitude _p > 0.1) exitWith { _offset = _p; };
    } forEach ["exhaust", "exhaust1", "exhaust2", "exhaust_l", "exhaust_r"];
    if (vectorMagnitude _offset < 0.1) then { _offset = [0, -2, 0.6]; };
    _offset
};

// Sync: keep a source while its vehicle is in the plan, delete it otherwise.
private _live = [];
{
    private _rec = _x;
    private _src = _rec getOrDefault ["source", objNull];
    private _rveh = _rec getOrDefault ["veh", objNull];
    private _idx = _plan findIf { (_x getOrDefault ["veh", objNull]) isEqualTo _rveh };
    private _keep = !isNull _src && !isNull _rveh && alive _rveh && _idx >= 0;
    if (_keep) then {
        private _entry = _plan select _idx;
        private _depth = _entry getOrDefault ["depth", 0.5];
        private _alpha = _alphaMax * (((_entry getOrDefault ["mag", 0]) / 2.5) min 1);
        private _liveN = [_depth, _OVERDRAW_BUDGET, _MAX_SOURCES, _MAX_LIVE, _MIN_LIVE] call _liveCount;
        private _drop = _LIFETIME / _liveN;
        [_src, _depth, _alpha, _LIFETIME, _drop] call _applyParams;
        _live pushBack _rec;
    } else {
        if (!isNull _src) then { deleteVehicle _src; };
    };
} forEach _records;

// Create a source for each planned vehicle that has none yet.
{
    private _entry = _x;
    private _cveh = _entry getOrDefault ["veh", objNull];
    if (isNull _cveh) then { continue; };
    if ((_live findIf { (_x getOrDefault ["veh", objNull]) isEqualTo _cveh }) >= 0) then { continue; };

    private _depth = _entry getOrDefault ["depth", 0.5];
    private _alpha = _alphaMax * (((_entry getOrDefault ["mag", 0]) / 2.5) min 1);
    private _liveN = [_depth, _OVERDRAW_BUDGET, _MAX_SOURCES, _MAX_LIVE, _MIN_LIVE] call _liveCount;
    private _drop = _LIFETIME / _liveN;
    private _offset = [_cveh] call _exhaustOffset;

    private _source = "#particlesource" createVehicleLocal [0, 0, 0];
    _source attachTo [_cveh, _offset];
    [_source, _depth, _alpha, _LIFETIME, _drop] call _applyParams;

    private _rec = createHashMapFromArray [["veh", _cveh], ["source", _source]];
    _live pushBack _rec;

    // Reap on vehicle death between environment ticks.
    [_cveh, _source, _rec] spawn {
        params ["_veh", "_src", "_record"];
        waitUntil {
            sleep 2;
            isNull _src || !alive _veh || isNull _veh
        };
        deleteVehicle _src;
        _record set ["source", objNull];
        private _current = missionNamespace getVariable [QGVAR(exhaustSources), []];
        _current = _current select { !isNull (_x getOrDefault ["source", objNull]) };
        missionNamespace setVariable [QGVAR(exhaustSources), _current];
    };
} forEach _plan;

missionNamespace setVariable [QGVAR(exhaustSources), _live];
