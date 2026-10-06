#include "..\script_component.hpp"

/*
Radio state line.

One grep of "radio state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call,
then AEE_LOG_DEBUG each tick, so it is readable without the trace switch
and cheap with it off.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _index = missionNamespace getVariable [QGVAR(radioPropagationIndex), 1.0];
if !(_index isEqualType 0) then { _index = 1.0; };
private _ionoAbs = missionNamespace getVariable [QEGVAR(core,ionosphericAbsorption), 0];
if !(_ionoAbs isEqualType 0) then { _ionoAbs = 0; };
private _frequency = missionNamespace getVariable [QGVAR(frequency), 3e6];
if !(_frequency isEqualType 0) then { _frequency = 3e6; };
private _sunspotNumber = missionNamespace getVariable [QGVAR(sunspotNumber), 100];
if !(_sunspotNumber isEqualType 0) then { _sunspotNumber = 100; };
private _radioFrequencyHz = missionNamespace getVariable [QGVAR(radioFrequencyHz), 1e8];
if !(_radioFrequencyHz isEqualType 0) then { _radioFrequencyHz = 1e8; };
private _radioLinkRangeM = missionNamespace getVariable [QGVAR(radioLinkRangeM), 5000];
if !(_radioLinkRangeM isEqualType 0) then { _radioLinkRangeM = 5000; };
private _txPower = missionNamespace getVariable [QGVAR(txPower), 37];
if !(_txPower isEqualType 0) then { _txPower = 37; };
private _propagationRange = missionNamespace getVariable [QGVAR(propagationRange), 2.0];
if !(_propagationRange isEqualType 0) then { _propagationRange = 2.0; };

private _logMsg = format [
    "radio state | index=%1 iono=%2 | link=frequency=%3 sunspot=%4 carrier=%5 range=%6 tx=%7 ceiling=%8",
    round (_index * 100) / 100, round (_ionoAbs * 100) / 100,
    _frequency, _sunspotNumber, _radioFrequencyHz, _radioLinkRangeM, _txPower, round (_propagationRange * 100) / 100
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
