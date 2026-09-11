#include "..\script_component.hpp"

/*
Lightning strike risk index and periodic strike generation.

Risk computed from overcast, rain, humidity, and convective potential
(temp >25°C or rapid temperature drop).  Strike occurs at a random
nearby open position when risk exceeds 0.5 and a probability roll passes.

Sets:
  QGVAR(currentLightningRisk)   — float 0-1
  QGVAR(currentLightningStrike) — bool (true = strike this tick)
  QGVAR(lastLightningPos)       — [x,y,z] or [] if none
  QGVAR(lastStrikeTime)         — diag_tickTime of last strike
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
private _overcast = overcast;
private _rain = rain;
private _RH = EGVAR(core,currentHumidity);
private _temp = EGVAR(core,currentTemperature);

if (isNil "_RH")   then { _RH = 50; };
if (isNil "_temp") then { _temp = 20; };

// ─── Convective potential ────────────────────────────────────────────────
// Elevated surface temp OR rapid cooling between ticks indicates
// unstable air capable of producing Cb clouds.
private _lastTemp = missionNamespace getVariable [QGVAR(lastTemperature), _temp];
private _tempDrop = (_lastTemp - _temp) max 0;

private _convective = 0;
if (_temp > 25)     then { _convective = 1; };
if (_tempDrop > 3)  then { _convective = _convective max 0.8; };

missionNamespace setVariable [QGVAR(lastTemperature), _temp];

// ─── Risk index (0-1) ───────────────────────────────────────────────────
private _risk = (_overcast * 0.3 + _rain * 0.3 + (_RH / 100) * 0.2 + _convective * 0.2) min 1.0;

// ─── Strike generation ──────────────────────────────────────────────────
// At max risk: 5 %/tick; at threshold (0.5): 2.5 %/tick
private _strike = false;
private _strikePos = [];

if (_risk > 0.5 && random 1 < _risk * 0.05) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player" && alive _player) then {
        private _playerPos = getPos _player;
        private _dist  = 50 + random 250;   // 50-300 m away
        private _dir   = random 360;
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
missionNamespace setVariable [QGVAR(currentLightningRisk),   _risk];
missionNamespace setVariable [QGVAR(currentLightningStrike), _strike];
missionNamespace setVariable [QGVAR(lastLightningPos),       _strikePos];
missionNamespace setVariable [QGVAR(lastStrikeTime),         [diag_tickTime, missionNamespace getVariable [QGVAR(lastStrikeTime), -1]] select (!_strike)];
