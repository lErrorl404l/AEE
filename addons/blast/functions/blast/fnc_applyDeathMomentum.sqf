#include "..\..\script_component.hpp"
/*
Death momentum (issue #161, the death-moment half; the #160 blast
displacement is the same operation and is applied here).

On the Killed event the body's velocity is biased along the blast wind.
The engine picks the ragdoll pose; AEE biases only the initial momentum.

The blast is read from the record the Explosion handler publishes
(GVAR(lastBlast) = [originATL, massKg, missionTime]).  The overpressure
and the injury probabilities come from the EXISTING blast model
(FUNC(calculateBlastOverpressure), FUNC(calculateBlastInjury)); the throw
velocity from FUNC(calculateBlastThrow).

CEILING.  The engine documents no statement that a ragdoll inherits the
unit's velocity at death; setVelocity on a corpse is UNDOCUMENTED.  If
the ragdoll ignores it, this bias does not show (the #161 first test
vector decides it).  The blast record is machine-local, so a corpse on
another machine is not reached.

Input:  [_unit]
Output: [appliedVelocityVector, tumbleRate_radps]
*/
params [["_unit", objNull, [objNull]]];

if (isNull _unit) exitWith { [velocity _unit, 0] };

private _vel = velocity _unit;
private _omega = 0;

private _rec = missionNamespace getVariable [QGVAR(lastBlast), []];
if (_rec isEqualType [] && {(count _rec) == 3}) then {
    _rec params ["_origin", "_massKg", "_time"];
    private _age = CBA_missionTime - _time;
    private _dist = (_unit distance _origin) max 0.5;
    // A death within this window of the recorded blast is treated as a
    // blast kill.  A matching tolerance, not a physical constant.
    private _window = 2;
    if ((_age >= 0) && (_age < _window) && (_dist < 150)) then {
        // The existing blast model, reused.
        private _op = [_massKg, _dist] call FUNC(calculateBlastOverpressure);
        _op params ["_pSo", "_td"];
        if (_pSo > 0) then {
            private _inj = [_pSo, _td] call FUNC(calculateBlastInjury);
            // The #132 tertiary-throw probability is the gate.
            if ((_inj select 5) > 0) then {
                private _bodyMass = [_unit] call EFUNC(clothing,getCorpseMass);
                private _throw = [_pSo, _td, _bodyMass] call FUNC(calculateBlastThrow);
                _throw params ["_speed", "_omegaOut"];
                // The blast wind blows radially outward from the origin.
                private _dir = (getPosATL _unit) vectorDiff _origin;
                if ((vectorMagnitude _dir) < 0.01) then { _dir = [0, 0, 1]; };
                _vel = _vel vectorAdd ((vectorNormalized _dir) vectorMultiply _speed);
                _omega = _omegaOut;
            };
        };
    };
};

_unit setVelocity _vel;
[_vel, _omega]
