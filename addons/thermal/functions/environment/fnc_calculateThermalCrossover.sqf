#include "..\..\script_component.hpp"

/*
Diurnal thermal crossover detection — nullifies thermal optic contrast.

When ambient air temperature and ground surface temperature converge within
~1.5 °C, the thermal gradient disappears and FLIR/IR systems lose contrast.
A sustained timer (~1 tick ≈ 5 s) prevents brief fluctuations from
triggering false positives.

The surface temperature is the FIRST LAYER of the four-layer ground node
stack (fnc_calculateGroundNodeStack, issue #198), so crossover reads the
same surface every other thermal consumer exchanges with.  The ground-state
offsets below are a fallback only, for the impossible empty stack, and are
UNSOURCED.

Stored in GVAR(thermalCrossoverActive) (bool) and GVAR(surfaceTemperature).
*/

private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _overcast = overcast;

// ─── Surface temperature from the four-layer ground node stack ───────────
// Resolve the position the way the node stack does: the current unit's ASL
// position, else the map origin.  One stack call per tick, so the
// time-integrated state advances once.
private _pos = [];
private _unit = call CBA_fnc_currentUnit;
if (!isNil "_unit" && {!isNull _unit}) then { _pos = getPosASL _unit; };
if (count _pos < 2) then { _pos = [0, 0, 0]; };

private _stack = [_pos] call FUNC(calculateGroundNodeStack);
private _surfaceTemp = _stack select 0;

// Fallback for the impossible empty stack.  The ground-state offsets are
// UNSOURCED and a normal run never reaches them.
if (_stack isEqualTo []) then {
    _surfaceTemp = switch (_groundState) do {
        case "Snow":   { _airTemp - 2 };
        case "Mud":    { _airTemp - 1 };
        case "Dusty":  { _airTemp + 5 };
        case "Frozen": { _airTemp - 3 };
        default        { _airTemp + 2 * (1 - _overcast) }; // Normal: solar heating
    };
};

// ─── Crossover only in the twilight window ─────────────────────────────
// True thermal crossover (isothermal condition) happens when the surface
// and air equilibrate — at dawn and dusk, when solar heating is passing
// through zero.  The naive air-vs-surface delta fires at NIGHT too
// (surface cools to air temp), but a FLIR still sees objects as warm
// against the cool background — night is when thermal is most useful.
//
// Gate on solar elevation, and do NOT clamp the sine to 0.  A clamped
// `max 0` makes midnight identical to sunrise (both report 0°), which
// fires the twilight gate all night and nullifies thermal exactly when
// it should work best.  Instead the sine must go negative below the
// horizon, and twilight means the sun is within ~10° of the horizon on
// EITHER side — dawn and dusk only.
private _dayFraction = dayTime / 24;
private _sunElev = sin ((_dayFraction - 0.25) * 360) * 90;
private _inTwilight = abs _sunElev < 10;

private _delta = abs (_airTemp - _surfaceTemp);
private _crossoverNow = _inTwilight && _delta <= 1.5;

// ─── Timer accumulator — sustain for ~1 tick ──────────────────────────
private _timer = missionNamespace getVariable [QEGVAR(core,crossoverTimer), 0];

if (_crossoverNow) then {
    _timer = _timer + 1;
} else {
    _timer = _timer - 1;
};

_timer = _timer max -6 min 6;

private _active = _timer > 1;

missionNamespace setVariable [QEGVAR(core,crossoverTimer), _timer];
missionNamespace setVariable [QEGVAR(core,thermalCrossoverActive), _active];
missionNamespace setVariable [QEGVAR(core,surfaceTemperature), _surfaceTemp];

_active
