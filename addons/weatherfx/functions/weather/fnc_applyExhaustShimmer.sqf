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
  4. the DERIVED air-vehicle term for an Air class, from the real air power
     balance.  See below.  THIS BRANCH IS OUTSIDE THE difficultyEnabledRTD
     GUARD ON PURPOSE: with the SIMPLE flight model the RTD reader is
     unavailable, and reaching this branch then is the whole point
  5. otherwise the declared idle fraction, so a parked aircraft and a land
     vehicle at rest still show a small plume rather than nothing
The reader is gated on the flight model and is unavailable when it is off.
The derived air term is NOT gated on the flight model, so an aircraft in the
simple flight model still grows its plume with airspeed.

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

AN AIRCRAFT IN THE SIMPLE FLIGHT MODEL IS OTHERWISE PINNED TO THE DECLARED
IDLE.  difficultyEnabledRTD is false in the simple flight model, so the RTD
reader is skipped, and an aircraft is not a LandVehicle, so the ground term
is skipped too.  Before this term existed an aircraft resolved to the idle
0.05 for the whole flight, however hard it climbed.  The air term is DERIVED
from the power balance in fnc_calculateAirEngineLoad, and the object work
stays here: this function reads the class with typeOf, the mass with getMass,
the speed with velocity, the published air density, and the per-vehicle
overrides.  A wing uses the drag power 0.5 rho (Cd S) v^3, so the plume grows
with the CUBE of airspeed; a rotor uses the ideal induced hover power
W^1.5 / sqrt (2 rho A), which is a stated lower bound.  The rated power is
read from the optional aee_engineRatedPowerW the ground term uses, then the
aircraft catalogue under data/aircraft/ through the generated getAircraftData
lookup, then the declared defaults.  The drag area and the rotor disc area
follow the same order from aee_engineDragAreaM2 and aee_engineRotorDiscAreaM2.
The declared defaults are the empty-row fallback, not measurements.

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

The mobility value aee_vehicles_enginePowerModifier is NOT used, because it
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

A THROTTLED DIAGNOSTIC MAKES THE PLUME OBSERVABLE.  This renderer emitted no
log line at all, so a session could not tell whether the aircraft plume ran;
the 49 shimmer matches in an RPT were all the unrelated optics ChromAberration
term.  One debug line per candidate vehicle per window now names the vehicle,
its class, the resolved tier, the power fraction, the gas temperature, the
plume depth, the contrast magnitude and the alpha the renderer will draw.  It
is gated on the aee_particles_logDebug setting through AEE_LOG_DEBUG, so it costs
nothing until that box is ticked, and it is throttled on diag_tickTime to one
batch per _LOG_INTERVAL, 30 s.  The caller drives this on the environment
tick, which runs every aee_core_updateInterval seconds (5 s by default), so
the window is honest: at most one batch per six ticks.

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
// The diagnostic window.  The caller drives this on the environment tick,
// which runs every aee_core_updateInterval seconds (5 s by default), so a
// 30 s window yields at most one diagnostic batch per six ticks.  That is
// often enough to prove the plume path ran and rare enough not to flood the
// RPT.  The window is timed on diag_tickTime, not on a tick counter.
private _LOG_INTERVAL = 30;

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
    private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
    if !(_rho isEqualType 0) then { _rho = AERO_ISA_SEA_LEVEL_DENSITY; };
    private _rated = _veh getVariable ["aee_engineRatedPowerW", 150000];
    if !(_rated isEqualType 0) then { _rated = 150000; };

    [_force, _speed, getMass _veh, _smooth, _rated, _idlePower, 0, _rho] call EFUNC(vehicles,calculateEngineLoad)
};

// ─── Derived air-vehicle load ──────────────────────────────────────────────
// An aircraft in the simple flight model has no RTD reader, so the load is
// derived from a real power balance: the drag power for a wing and the ideal
// induced hover power for a rotor.  The object work stays here and the kernel
// is pure arithmetic.  See the header and fnc_calculateAirEngineLoad.
private _deriveAirPower = {
    params ["_veh", "_idlePower"];
    private _speed = vectorMagnitude (velocity _veh);

    // The four flight-model scalars come from the aircraft corpus under
    // data/aircraft/ through the generated lookup. A per-vehicle override
    // wins, then the catalogue row, then the declared default. The corpus
    // row holds [mass kg, rated power W, drag area m2, rotor disc area m2];
    // an absent field is a labelled zero. See gen_aircraft_data.py.
    private _row = [typeOf _veh] call EFUNC(flight,getAircraftData);
    private _rowHeld = _row isEqualType [] && {count _row == 4};
    private _corpusMass = if (_rowHeld) then { _row select 0 } else { 0 };
    private _corpusRated = if (_rowHeld) then { _row select 1 } else { 0 };
    private _corpusDrag = if (_rowHeld) then { _row select 2 } else { 0 };
    private _corpusDisc = if (_rowHeld) then { _row select 3 } else { 0 };

    private _mass = if (_corpusMass > 0) then { _corpusMass } else { getMass _veh };

    private _rated = _veh getVariable ["aee_engineRatedPowerW", 0];
    if !(_rated isEqualType 0) then { _rated = 0; };
    if (_rated <= 0) then { _rated = _corpusRated; };
    if (_rated <= 0) then { _rated = 150000; };

    private _dragArea = _veh getVariable ["aee_engineDragAreaM2", 0];
    if !(_dragArea isEqualType 0) then { _dragArea = 0; };
    if (_dragArea <= 0) then { _dragArea = _corpusDrag; };
    if (_dragArea <= 0) then { _dragArea = 0.7; };

    private _discArea = _veh getVariable ["aee_engineRotorDiscAreaM2", 0];
    if !(_discArea isEqualType 0) then { _discArea = 0; };
    if (_discArea <= 0) then { _discArea = _corpusDisc; };
    if (_discArea <= 0) then { _discArea = 50; };

    private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
    if !(_rho isEqualType 0) then { _rho = AERO_ISA_SEA_LEVEL_DENSITY; };

    [_mass, _speed, typeOf _veh, _rated, _dragArea, _discArea, _idlePower, _rho] call EFUNC(flight,calculateAirEngineLoad)
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
    if (_power < 0) then {
        // An aircraft in the simple flight model reaches neither the RTD
        // reader nor the land term, so its load is derived from the air
        // power balance.  This branch MUST sit OUTSIDE the difficultyEnabledRTD
        // guard: reaching it with the flight model OFF is the whole point.
        // Gated on the air root, not on Helicopter or Plane, so a third air
        // root cannot fall through to the idle.  See the header.
        if (_veh isKindOf "Air") then {
            private _derivedAir = [_veh, _idlePower] call _deriveAirPower;
            if (_derivedAir >= 0) then { _power = _derivedAir; };
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

// The render alpha is the declared ceiling scaled by the contrast.  It is read
// here, before the plan, so the diagnostic can report the alpha the renderer
// will draw.  It stays the ONLY free visibility lever.  See the header.
private _alphaSetting = missionNamespace getVariable [QGVAR(exhaustShimmerAlpha), 0.15];
if !(_alphaSetting isEqualType 0) then { _alphaSetting = 0.15; };

// Heat haze (aee-workshop-copy item 7, part 2).  The ambient temperature
// scales the peak alpha, re-derived from Better Visuals fn_heatHaze.  The
// kernel is pure and takes the temperature NUMBER (ambientTemperature
// element 0), the floor 0.15 and the ceiling from the heatHazeMaxAlpha
// setting.  A 20 C reference keeps the default look unchanged, so the change
// is temperature coupling and not a blanket dimming.  See fnc_heatHazeAlpha.
private _heatHazeEnabled = missionNamespace getVariable [QGVAR(heatHazeEnabled), true];
private _heatHazeMax = missionNamespace getVariable [QGVAR(heatHazeMaxAlpha), 0.45];
if !(_heatHazeMax isEqualType 0) then { _heatHazeMax = 0.45; };
private _airTempC = 20;
if (ambientTemperature isEqualType []) then {
    if ((count ambientTemperature) > 0) then {
        private _firstTemp = ambientTemperature select 0;
        if (_firstTemp isEqualType 0) then { _airTempC = _firstTemp; };
    };
};
private _hazeAlpha = [_airTempC, 0.15, _heatHazeMax] call EFUNC(particles,heatHazeAlpha);
private _hazeScale = 1;
if (_heatHazeEnabled) then {
    private _hazeRef = [20, 0.15, _heatHazeMax] call EFUNC(particles,heatHazeAlpha);
    // Guard the reference: heatHazeMaxAlpha 0 makes the 20 C reference 0, so
    // the raw ratio divides by zero.  A zero ceiling disables the temperature
    // coupling, so the scale is the neutral 1.
    _hazeScale = if (_hazeRef > 0) then {
        ((_hazeAlpha / _hazeRef) max 0.2) min 1.5
    } else {
        1
    };
};

// The matcher publishes the per-world haze scale as element 3 of
// aee_lighting_worldLighting.  Default 1 when it has not run.  The
// grain path reads the same array (fnc_applyWeatherGrain reads element 2),
// so the star, grain and haze elements all have a consumer.
private _worldProfile = missionNamespace getVariable [QEGVAR(lighting,worldLighting), [1, 1, 1, 1]];
private _hazeWorldScale = 1;
if ((_worldProfile isEqualType []) && {(count _worldProfile) > 3}) then {
    _hazeWorldScale = _worldProfile select 3;
};
if !(_hazeWorldScale isEqualType 0) then { _hazeWorldScale = 1; };

private _alphaMax = _alphaSetting * _hazeScale * _hazeWorldScale;

// The diagnostic throttle.  One batch per _LOG_INTERVAL, timed on diag_tickTime
// because the caller drives this on the environment tick, not per frame.
private _logAt = missionNamespace getVariable [QGVAR(exhaustLogAt), -1e9];
if !(_logAt isEqualType 0) then { _logAt = -1e9; };
private _logNow = diag_tickTime >= _logAt;
if (_logNow) then {
    missionNamespace setVariable [QGVAR(exhaustLogAt), diag_tickTime + _LOG_INTERVAL];
};

{
    private _cand = _x;
    private _tier = [_cand, _TIERS] call _selectTier;
    private _row = _TIERS getOrDefault [_tier, _TIERS get "land"];
    _row params ["_idleT", "_fullT", "_idleD", "_fullD"];

    // The power fraction drives the plume size, not the alpha.
    private _power = [_cand, _IDLE_POWER, _ACCEL_TAU] call _resolvePower;
    private _profile = [_power, _idleT, _fullT, _idleD, _fullD] call EFUNC(vehicles,calculateExhaustPlume);
    private _gasC = _profile select 0;
    private _depth = _profile select 1;

    // A measured per-vehicle value wins over the declared class row.
    private _gasOverride = _cand getVariable ["aee_exhaustGasTempC", -1];
    if (_gasOverride isEqualType 0 && _gasOverride > 0) then { _gasC = _gasOverride; };
    private _depthOverride = _cand getVariable ["aee_exhaustPlumeM", -1];
    if (_depthOverride isEqualType 0 && _depthOverride > 0) then { _depth = _depthOverride; };

    // Heat-haze sprite size (aee-workshop-copy item 7, part 2).  One draw per
    // vehicle, held on the vehicle, so the sprite size is stable across
    // ticks.  The kernel is pure; 1.0 is the identity, and the pending
    // overdraw budget recomputes from the scaled depth.  See fnc_heatHazeSize.
    if (_heatHazeEnabled) then {
        private _hazeRng = _cand getVariable ["aee_exhaustHazeRng", -1];
        if !(_hazeRng isEqualType 0) then { _hazeRng = -1; };
        if (_hazeRng < 0) then {
            _hazeRng = random 1;
            _cand setVariable ["aee_exhaustHazeRng", _hazeRng];
        };
        _depth = _depth * ([_hazeRng] call EFUNC(particles,heatHazeSize));
    };

    private _contrast = [_gasC, _airC, _rhoRel] call EFUNC(hydrology,calculateThermalRefraction);
    private _mag = abs _contrast;
    if (_mag > _maxMag) then { _maxMag = _mag; };

    // The diagnostic.  A renderer that cannot be observed cannot be debugged,
    // so one throttled line names the vehicle, its class, the resolved tier,
    // the power fraction, the gas temperature, the plume depth, the contrast
    // magnitude and the alpha the renderer will draw.  AEE_LOG_DEBUG is gated
    // on the aee_particles_logDebug setting, so this costs nothing until that box is
    // ticked, and _logNow throttles it to one batch per _LOG_INTERVAL.
    if (_logNow) then {
        private _logAlpha = _alphaMax * ((_mag / 2.5) min 1);
        private _logMsg = format [
            "exhaust plume: %1 class=%2 tier=%3 power=%4 gasC=%5 depth=%6 contrast=%7 alpha=%8",
            netId _cand, typeOf _cand, _tier, _power, _gasC, _depth, _mag, _logAlpha
        ];
        AEE_LOG_DEBUG(_logMsg);
    };

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
