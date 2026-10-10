#include "..\..\script_component.hpp"
/*
Corpse physics (issue #160): the whole-body physical interaction of a
dead body with AEE's models.  On the Killed event:

  - Mass: the corpse's mass is the body plus the carried load
    (FUNC(calculateCorpseMass)), applied with setMass.
  - Blast displacement and tumble: the linear throw comes from the blast
    wind via FUNC(applyDeathMomentum); the tumble rate from the same
    blast is applied here with setAngularVelocity.

The thermal fade (a dead body cooling toward ambient) is ALREADY modelled
by aee_thermal: FUNC(calculateObjectTemperature) has a DEAD branch
(Newton's law of cooling, tau 7200 s ~ 1 C/h, Henssge).  No second
thermal model is added here.

CEILING.  setMass and setAngularVelocity on a corpse are UNDOCUMENTED;
the engine may not apply them to a dead unit consistently (verify
in-game).

Input:  [_unit]
Output: BOOL - true when the physics was applied
*/
params [["_unit", objNull, [objNull]]];

if (isNull _unit) exitWith { false };

// Mass: the body plus the carried load.
private _mass = [_unit] call EFUNC(clothing,getCorpseMass);
_unit setMass _mass;

// The linear death momentum (the blast wind); returns the tumble rate.
private _mom = [_unit] call FUNC(applyDeathMomentum);
_mom params ["_vel", "_omega"];

// Tumble: rotate about a horizontal axis perpendicular to the throw.
if (_omega isEqualType 0 && (_omega > 0)) then {
    private _axis = [1, 0, 0];
    if ((_vel isEqualType []) && {(vectorMagnitude _vel) > 0.01}) then {
        private _perp = (vectorNormalized _vel) vectorCrossProduct [0, 0, 1];
        if ((vectorMagnitude _perp) > 0.01) then {
            _axis = vectorNormalized _perp;
        };
    };
    _unit setAngularVelocity (_axis vectorMultiply (_omega min 1000));
};

true
