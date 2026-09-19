#include "..\..\script_component.hpp"

/*
Lightning strike risk index and periodic strike generation.

Risk computed from overcast, rain, humidity, convective potential
(temp above the configured threshold or rapid temperature drop), and the
ice-phase gate. Lightning
needs deep convection with an ice phase in the mixed-phase region
(-10 to -20°C). Non-inductive charging between graupel and ice crystals
is the main charge source (Saunders 1993). Strike occurs at a random
nearby open position when risk exceeds 0.5 and a probability roll passes.

Sets:
  QEGVAR(core,currentLightningRisk)   - float 0-1
  QGVAR(currentLightningStrike) - bool (true = strike this tick)
  QGVAR(lastLightningPos)       - [x,y,z] or [] if none
  QGVAR(lastStrikeTime)         - diag_tickTime of last strike
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
// Zeus storm override: "thunderstorm" forces the risk, "clear" zeroes it.
private _overrideType     = missionNamespace getVariable [QEGVAR(core,stormOverrideType), ""];
private _overrideUntil    = missionNamespace getVariable [QEGVAR(core,stormOverrideUntil), 0];
private _overridden       = false;
if ((_overrideType != "") && (time < _overrideUntil)) then {
    private _overrideIntensity = missionNamespace getVariable [QEGVAR(core,stormOverrideIntensity), 0.5];
    _overrideIntensity = _overrideIntensity max 0 min 1;
    if (_overrideType == "clear") then {
        missionNamespace setVariable [QEGVAR(core,currentLightningRisk), 0];
        _overridden = true;
    };
    if (_overrideType == "thunderstorm") then {
        missionNamespace setVariable [QEGVAR(core,currentLightningRisk), _overrideIntensity];
        missionNamespace setVariable [QGVAR(lastTemperature), EGVAR(core,currentTemperature)];
        _overridden = true;
    };
};
if (_overridden) exitWith {};

private _overcast = overcast;
private _rain = rain;
private _RH = EGVAR(core,currentHumidity);
private _temp = EGVAR(core,currentTemperature);

if (isNil "_RH")   then { _RH = 50; };
if (isNil "_temp") then { _temp = 20; };

// ─── Settings ─────────────────────────────────────────────────────────────
private _convectionTemp = missionNamespace getVariable [QGVAR(lightningConvectionTemp), 25];
private _interval       = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _strikeChance   = missionNamespace getVariable [QGVAR(lightningStrikeChance), 0.05];
_strikeChance = _strikeChance * (_interval / 5);

// ─── Convective potential ────────────────────────────────────────────────
// Elevated surface temp OR rapid cooling between ticks indicates
// unstable air capable of producing Cb clouds.
private _lastTemp = missionNamespace getVariable [QGVAR(lastTemperature), _temp];
private _tempDrop = (_lastTemp - _temp) max 0;

private _convective = 0;
if (_temp > _convectionTemp) then { _convective = 1; };
if (_tempDrop > 3)  then { _convective = _convective max 0.8; };

missionNamespace setVariable [QGVAR(lastTemperature), _temp];

// ─── Risk index (0-1) ───────────────────────────────────────────────────
private _risk = (_overcast * 0.3 + _rain * 0.3 + (_RH / 100) * 0.2 + _convective * 0.2) min 1.0;

// ─── Ice-phase gate ─────────────────────────────────────────────────────
// Deep clouds must reach the mixed-phase region for charge separation.
// The cloud ceiling gives the cloud top. Below 5500 m the ice phase is
// weak or absent; at 8000 m it is fully developed.
private _cloudTop = missionNamespace getVariable [QEGVAR(core,cloudCeiling_m), 0];
private _iceFactor = ((_cloudTop - 5500) / 2500) min 1 max 0;
_risk = _risk * _iceFactor;

// ─── Strike generation ──────────────────────────────────────────────────
// At max risk: configured chance per tick; at threshold (0.5): half that
private _strike = false;
private _strikePos = [];

if ((_risk > 0.5) && (([round (time * 10), 301] call EFUNC(core,deterministicRandom)) < (_risk * _strikeChance))) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && alive _player) then {
        private _playerPos = getPos _player;
        private _dist  = 50 + (250 * ([round (time * 10), 302] call EFUNC(core,deterministicRandom)));   // 50-300 m away
        private _dir   = 360 * ([round (time * 10), 303] call EFUNC(core,deterministicRandom));
        private _testX = (_playerPos#0) + sin _dir * _dist;
        private _testY = (_playerPos#1) + cos _dir * _dist;
        private _testPos = [_testX, _testY];

        // Avoid buildings >5 m overhead
        private _building = nearestBuilding _testPos;
        private _blocked = false;
        if (!isNull _building && _testPos distance2D _building < 50) then {
            private _bbox = boundingBoxReal _building;
            private _height = abs ((_bbox#1)#2 - (_bbox#0)#2);
            if (_height > 5) then { _blocked = true; };
        };

        if (!_blocked) then {
            _strike = true;
            _strikePos = [_testX, _testY, getTerrainHeightASL _testPos];
        };
    };
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,currentLightningRisk),   _risk];
missionNamespace setVariable [QGVAR(currentLightningStrike), _strike];
missionNamespace setVariable [QGVAR(lastLightningPos),       _strikePos];
missionNamespace setVariable [QGVAR(lastStrikeTime),         [diag_tickTime, missionNamespace getVariable [QGVAR(lastStrikeTime), -1]] select (!_strike)];
