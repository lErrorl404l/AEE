#include "..\..\script_component.hpp"

/*
Consolidated night-sky state line.

One grep of "sky state" answers whether each night-sky feature is active and,
when it is not, which gate turned it off.  The line carries the physical gates
(sun elevation, overcast, limiting magnitude, Kp, latitude), the render counts,
the force-hook values and the settings.  It is emitted once at AEE_LOG_INFO on
the first environment tick, then at AEE_LOG_DEBUG every tick, so the state is
readable without the trace switch and cheap with it off.

The line never changes the physics.  It reads the render registries that the
client workers publish, with safe defaults so the first line is valid before
the aurora and Milky Way workers (tasks 7 to 11) have run.

Debug hooks, set on missionNamespace:
  - aee_environmental_skyForce     Boolean, force the whole night sky on
  - aee_environmental_auroraForce  Number, -1 off, 0..1 forces that intensity
  - aee_environmental_milkyWayForce Boolean, force the Milky Way on
  - aee_environmental_starsForce   Number, forced limiting magnitude (6.5 reveals the faint bulk)
  - aee_environmental_meteorForce  String, one-shot shower code (spawns one meteor)
*/

private _skyForce = missionNamespace getVariable ["aee_environmental_skyForce", false];
private _auroraForce = missionNamespace getVariable ["aee_environmental_auroraForce", -1];
private _milkyWayForce = missionNamespace getVariable ["aee_environmental_milkyWayForce", false];
private _starsForce = missionNamespace getVariable ["aee_environmental_starsForce", 0];
private _meteorForce = missionNamespace getVariable ["aee_environmental_meteorForce", ""];
if !(_skyForce isEqualType false) then { _skyForce = false; };
if !(_auroraForce isEqualType 0) then { _auroraForce = -1; };
if !(_milkyWayForce isEqualType false) then { _milkyWayForce = false; };
if !(_starsForce isEqualType 0) then { _starsForce = 0; };

private _settingStars = missionNamespace getVariable [QGVAR(dynamicStars), true];
private _settingMeteors = missionNamespace getVariable [QGVAR(dynamicMeteors), true];
private _settingAurora = missionNamespace getVariable [QGVAR(dynamicAurora), true];
private _settingMilkyWay = missionNamespace getVariable [QGVAR(dynamicMilkyWay), true];

// Physical gates.
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _nelm = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
if !(_nelm isEqualType 0) then { _nelm = 6.5; };
private _kp = missionNamespace getVariable [QGVAR(kpIndex), 0];
if !(_kp isEqualType 0) then { _kp = 0; };
private _daytime = dayTime;
private _lat = ([] call EFUNC(core,getWorldLocation)) select 1;
if !(_lat isEqualType 0) then { _lat = 45; };
private _ovalLimit = 65 - ((_kp min 9) * 1.7);

// Active meteor shower codes for the meteors field.
private _activeCodes = [];
private _month = date select 1;
private _day = date select 2;
{
    if ([_month, _day, _x] call FUNC(showerIsActive)) then {
        _activeCodes pushBack (_x select 0);
    };
} forEach ([] call FUNC(meteorShowers));
private _showerActive = _activeCodes isNotEqualTo [];

// Render registries, with defaults so the first line is valid.
private _starLights = missionNamespace getVariable [QGVAR(starLights), []];
private _visibleStars = missionNamespace getVariable [QGVAR(visibleStars), []];
private _faintStarCount = missionNamespace getVariable [QGVAR(faintStarCount), 0];
private _meteors = missionNamespace getVariable [QGVAR(meteors), []];
private _auroraIntensity = missionNamespace getVariable [QGVAR(auroraIntensity), 0];

// Compose the whole-sky force into each feature before the gate kernel runs.
private _gStars = ["stars", _settingStars || _skyForce, (_starsForce > 0) || _skyForce, _sunElev, _overcast, _kp, _daytime, _lat, _ovalLimit, _nelm, _showerActive] call FUNC(skyGateReason);
private _gMeteors = ["meteors", _settingMeteors || _skyForce, _skyForce, _sunElev, _overcast, _kp, _daytime, _lat, _ovalLimit, _nelm, _showerActive] call FUNC(skyGateReason);
private _gAurora = ["aurora", _settingAurora || _skyForce, (_auroraForce >= 0) || _skyForce, _sunElev, _overcast, _kp, _daytime, _lat, _ovalLimit, _nelm, _showerActive] call FUNC(skyGateReason);
private _gMilkyWay = ["milkyway", _settingMilkyWay || _skyForce, _milkyWayForce || _skyForce, _sunElev, _overcast, _kp, _daytime, _lat, _ovalLimit, _nelm, _showerActive] call FUNC(skyGateReason);

private _starsField = if (_gStars select 0) then { "ON" } else { format ["OFF(%1)", _gStars select 1] };
private _meteorsField = if (_gMeteors select 0) then {
    if (_showerActive) then { format ["ON(%1)", _activeCodes joinString ","] } else { "ON" };
} else { format ["OFF(%1)", _gMeteors select 1] };
private _auroraField = if (_gAurora select 0) then { "ON" } else { format ["OFF(%1)", _gAurora select 1] };
private _milkyWayField = if (_gMilkyWay select 0) then { "ON" } else { format ["OFF(%1)", _gMilkyWay select 1] };

private _logMsg = format [
    "sky state | sun=%1 overcast=%2 nelm=%3 kp=%4 lat=%5 | stars=%6(emitters=%7/catalog=%8/faint=%9) | meteors=%10(active=%11) | aurora=%12(int=%13) | milkyway=%14 | forces=sky=%15 aurora=%16 mw=%17 stars=%18 meteor=%19 | settings=stars=%20 meteors=%21 aurora=%22 mw=%23",
    round _sunElev, _overcast, _nelm, _kp, round _lat,
    _starsField, count _starLights, count _visibleStars, _faintStarCount,
    _meteorsField, count _meteors,
    _auroraField, _auroraIntensity,
    _milkyWayField,
    _skyForce, _auroraForce, _milkyWayForce, _starsForce, _meteorForce,
    _settingStars, _settingMeteors, _settingAurora, _settingMilkyWay
];

if (missionNamespace getVariable [QGVAR(skyLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(skyLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
