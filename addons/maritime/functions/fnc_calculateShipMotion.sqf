#include "..\script_component.hpp"

/*
Ship motion driver (issue #33).

Reads the published sea state and the wind, resolves the vessels near the
player, calls the pure kernel fnc_shipMotionKernel, and publishes the
significant pitch, roll and heave per vessel and as a module aggregate.

The sea state is produced by fnc_calculateSeaState (Beaufort number and
significant wave height).  The peak wave period comes from the
Pierson-Moskowitz peak-frequency relation Tp = 0.730 * U with
U = sqrt(Hs / 0.0246), the same wind-speed relation the wave height uses,
so the period is consistent with the published wave height.  Source:
Pierson & Moskowitz 1964; Stewart, Introduction to Physical Oceanography
Ch.16.4.

Wave direction: the waves travel the way the wind blows toward, so the
travel direction is the meteorological FROM direction plus 180 degrees.

Sets (per vessel):  GVAR(shipPitch_deg), GVAR(shipRoll_deg),
                    GVAR(shipHeave_m), GVAR(shipMotionSeverity).
Sets (module):      the same four names on the mission namespace, from the
                    player's vessel when the player is afloat, otherwise
                    from the most severe vessel nearby.

Client only: the effect is local to the player.
*/

if (!hasInterface) exitWith {};
if !(missionNamespace getVariable [QEGVAR(core,maritimeEnabled), true]) exitWith {};

private _gm = missionNamespace getVariable [QGVAR(shipMetacentricHeight), 1.5];
if !(_gm isEqualType 0) then { _gm = 1.5; };
if (_gm <= 0) then { _gm = 1.5; };
private _zeta = missionNamespace getVariable [QGVAR(shipDamping), 0.10];
if !(_zeta isEqualType 0) then { _zeta = 0.10; };

private _waveH = missionNamespace getVariable [QGVAR(waveHeight_m), 0];
if !(_waveH isEqualType 0) then { _waveH = 0; };
private _windDir = missionNamespace getVariable [QEGVAR(core,currentWindDir), 0];
if !(_windDir isEqualType 0) then { _windDir = 0; };

private _waveTravelDir = _windDir + 180;
private _wavePeriod = 0.730 * sqrt (_waveH / 0.0246);

private _ships = nearestObjects [player, ["Ship"], 300];
private _playerShip = vehicle player;
if ((_playerShip isKindOf "Ship") && {!(_playerShip in _ships)}) then {
    _ships pushBack _playerShip;
};

private _aggPitch = 0;
private _aggRoll = 0;
private _aggHeave = 0;
private _aggSeverity = 0;
private _havePlayerShip = false;

{
    private _ship = _x;
    if (alive _ship) then {
        private _box = boundingBoxReal _ship;
        private _min = _box select 0;
        private _max = _box select 1;
        private _beam = abs ((_max select 1) - (_min select 1));
        private _length = abs ((_max select 0) - (_min select 0));
        private _mass = getMass _ship;

        private _motion = [
            _waveH, _wavePeriod, (speed _ship) / 3.6, _waveTravelDir - (getDir _ship),
            _beam, _length, _mass, _gm, _zeta
        ] call FUNC(shipMotionKernel);
        private _pitch = _motion select 0;
        private _roll = _motion select 1;
        private _heave = _motion select 2;
        private _severity = ((_roll max _pitch) / 25) min 1;

        _ship setVariable [QGVAR(shipPitch_deg), _pitch];
        _ship setVariable [QGVAR(shipRoll_deg), _roll];
        _ship setVariable [QGVAR(shipHeave_m), _heave];
        _ship setVariable [QGVAR(shipMotionSeverity), _severity];

        if (_ship isEqualTo _playerShip) then {
            _aggPitch = _pitch;
            _aggRoll = _roll;
            _aggHeave = _heave;
            _aggSeverity = _severity;
            _havePlayerShip = true;
        } else {
            if ((!_havePlayerShip) && (_severity > _aggSeverity)) then {
                _aggPitch = _pitch;
                _aggRoll = _roll;
                _aggHeave = _heave;
                _aggSeverity = _severity;
            };
        };
    };
} forEach _ships;

missionNamespace setVariable [QGVAR(shipPitch_deg), _aggPitch];
missionNamespace setVariable [QGVAR(shipRoll_deg), _aggRoll];
missionNamespace setVariable [QGVAR(shipHeave_m), _aggHeave];
missionNamespace setVariable [QGVAR(shipMotionSeverity), _aggSeverity];
