#include "..\..\script_component.hpp"

/*
Milky Way Draw3D worker, called once per frame by the handler that
fnc_renderMilkyWay registers.

Reads QGVAR(milkyWaySamples) (each entry [altDeg, azDeg]) and draws one line
segment per consecutive pair with drawLine3D, skipping any segment that has a
sample below the horizon.  The alpha scales with the NELM headroom above
MILKY_WAY_NELM_MIN, so the band stays faint.

The band is client-only, draws no object and consumes no dynamic light.
MILKY_WAY_SAMPLES + 1 draw calls is the ceiling; the loop makes at most one
fewer than the sample count.
*/

if (!(missionNamespace getVariable [QGVAR(milkyWayActive), false])) exitWith {};

private _samples = missionNamespace getVariable [QGVAR(milkyWaySamples), []];
private _count = count _samples;
if (_count < 2) exitWith {};

private _nelm = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
if !(_nelm isEqualType 0) then { _nelm = 6.5; };
private _headroom = ((_nelm - MILKY_WAY_NELM_MIN) / 1.5) max 0 min 1;
private _alpha = MILKY_WAY_ALPHA * (0.4 + 0.6 * _headroom);
private _colour = MILKY_WAY_COLOUR + [_alpha];

private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;

for "_i" from 0 to (_count - 2) do {
    private _a = _samples select _i;
    private _b = _samples select (_i + 1);
    private _altA = _a select 0;
    private _altB = _b select 0;
    if ((_altA >= 0) && (_altB >= 0)) then {
        private _dirA = [_a select 0, _a select 1] call FUNC(starDirection);
        private _dirB = [_b select 0, _b select 1] call FUNC(starDirection);
        private _p1 = _eyePos vectorAdd (_dirA vectorMultiply MILKY_WAY_RADIUS);
        private _p2 = _eyePos vectorAdd (_dirB vectorMultiply MILKY_WAY_RADIUS);
        drawLine3D [_p1, _p2, _colour];
    };
};
