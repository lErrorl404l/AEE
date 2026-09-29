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
  for contrast, a 5.56 mm object is 0.18 px at 50 m

A plume is metres across, so it is visible without exaggeration, unlike a
bullet.  The absence of a fudge constant is the finding, not an omission.

ALPHA IS THE ONLY FREE LEVER.  Fill rate is sprite count times sprite area
and never alpha, so visibility is bought with alpha alone.  The refract
billboard samples the framebuffer and is among the most expensive particle
types, so the emitter count and the sprite size are the budget.  The repo
measured 190 square metres of overdraw as acceptable and 642 square metres
as a stutter on 27 Sep 2026.  This renderer bounds the live sprite count
instead of the emission rate: each source holds at most _LIFETIME / _drop,
which is _MAX_LIVE sprites, and at most _MAX_SOURCES sources draw at once.
The worst case is _MAX_SOURCES * _MAX_LIVE * depth^2.  With the 2.0 m
afterburner depth that is 3 * 12 * 4 = 144 square metres, below the 190
that was measured as acceptable.

PER-CLASS PLUME DEPTHS, DECLARED AS DEFAULTS AND NOT AS MEASUREMENTS.  The
repository holds no measured exhaust data, so these are declared defaults:
  - helicopter / turboshaft, gas about 500 C, plume depth 0.5 m
  - fixed-wing aero engine, gas about 600 C, plume depth 0.8 m
  - afterburner / jet, gas about 1200 C, plume depth 2.0 m
The afterburner tier is not selected by kindOf, because no verified config
key distinguishes an afterburner from a dry aero engine.  A mod or mission
that holds a measured value publishes it on the vehicle as
aee_exhaustGasTempC (Celsius) and aee_exhaustPlumeM (metres); this function
reads both and falls back to the class default when they are absent.

EXHAUST GAS TEMPERATURE IS NOT REACHABLE FROM THE THERMAL SOLVER.  The AEE
thermal solver publishes aee_core_objectTemperatures as [object, surface
temperature] pairs and aee_thermal_selTemperature as a map of per-selection
SURFACE temperatures.  Neither is an exhaust GAS temperature; a surface
temperature sits near ambient plus solar and engine load, not at 500 to
1200 C.  So no reachable per-object exhaust gas temperature exists, and the
class default above is used instead, with the per-vehicle override for a
measured value.  This is stated rather than hidden.

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
record on aee_optics_exhaustSources, and the published contrast
aee_optics_exhaustRefraction.
*/

if (!hasInterface) exitWith {};
if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};
private _veh = vehicle _player;
if (cameraOn != _player && cameraOn != _veh) exitWith {};

// Budget constants.  See the header for the overdraw arithmetic.
private _LIFETIME = 1.2;
private _MAX_LIVE = 12;
private _MAX_SOURCES = 3;
private _MIN_CONTRAST = 0.1;
private _PLUME_RANGE = 250;
private _drop = _LIFETIME / _MAX_LIVE;

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
    // Declared class default: turboshaft, then aero for a fixed wing.
    private _profile = [500, 0.5];
    if (_cand isKindOf "Plane") then { _profile = [600, 0.8]; };
    private _gasC = _profile select 0;
    private _depth = _profile select 1;

    // A measured per-vehicle value, when the vehicle or a mod publishes one.
    private _gasOverride = _cand getVariable ["aee_exhaustGasTempC", -1];
    if (_gasOverride isEqualType 0 && _gasOverride > 0) then { _gasC = _gasOverride; };
    private _depthOverride = _cand getVariable ["aee_exhaustPlumeM", -1];
    if (_depthOverride isEqualType 0 && _depthOverride > 0) then { _depth = _depthOverride; };

    private _contrast = [_gasC, _airC, _rhoRel] call EFUNC(ballistics,calculateThermalRefraction);
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
// cannot drift apart.
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
