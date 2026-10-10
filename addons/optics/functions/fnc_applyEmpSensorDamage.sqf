#include "..\script_component.hpp"

/*
EMP optoelectronic upset (issue #9).

A nuclear EMP couples into an optical sensor's aperture and front-end and
upsets or damages the optoelectronic chain (photodetector, image intensifier,
thermal detector).  This function applies the degradation factor aee_core
publishes (fnc_updateEmp) to the shared optical attenuation, and drives the
image-intensifier blowout.

Device thresholds (issue #9): optoelectronics upset at 1 kV/m, damage at
5 kV/m.  The tube blowout is gated on the coupled field reaching the upset
threshold.

NVG AGC spike / tube damage: the nightvision tube model (fnc_applyNVGTubeModel)
reads QEGVAR(nightvision,nvgFlashUntil) as its blowout source.  The muzzle
flash path already stamps it; an EMP that exceeds the optoelectronic upset
threshold stamps it here for the recovery time the core model computes, so the
tube blooms and stays degraded.  The window is the core recovery time
constant (fnc_calculateEmpRecovery), not a fixed flash duration.

The function is a no-op when no EMP is active, so a normal mission is
unaffected.  It runs after fnc_calculateAttenuation on the same tick, so it
scales the fresh attenuation.

Arguments: None
Return Value: NUMBER - the applied sensor degradation factor (1.0 when intact)
Example: [] call aee_optics_fnc_applyEmpSensorDamage
Public: No
*/

private _active = missionNamespace getVariable [QEGVAR(core,empActive), false];
if (!_active) exitWith { 1 };

private _factor = missionNamespace getVariable [QEGVAR(core,empOpticsFactor), 1.0];
if !(_factor isEqualType 0) then { _factor = 1.0; };
if (_factor >= 1.0) exitWith { 1 };

private _coupled = missionNamespace getVariable [QEGVAR(core,empOpticsCoupledVpm), 0];
if !(_coupled isEqualType 0) then { _coupled = 0; };

private _tau = missionNamespace getVariable [QEGVAR(core,empOpticsTauS), 1];
if !(_tau isEqualType 0) then { _tau = 1; };

private _start = missionNamespace getVariable [QEGVAR(core,empStartTime), 0];
if !(_start isEqualType 0) then { _start = 0; };

private _f = _factor max 0.1 min 1.0;

// Degrade the shared optical transmission (laser/IR and visible bands).
private _laser = missionNamespace getVariable [QGVAR(currentLaserAttenuation), 1.0];
if !(_laser isEqualType 0) then { _laser = 1.0; };
private _visible = missionNamespace getVariable [QGVAR(currentVisibleAttenuation), 1.0];
if !(_visible isEqualType 0) then { _visible = 1.0; };

missionNamespace setVariable [QGVAR(currentLaserAttenuation), (_laser * _f) max 0.1 min 1.0];
missionNamespace setVariable [QGVAR(currentVisibleAttenuation), (_visible * _f) max 0.1 min 1.0];

// Image-intensifier blowout / tube damage once the coupled field reaches the
// optoelectronic upset threshold (1 kV/m).
if (_coupled >= 1000) then {
    private _until = _start + _tau;
    private _current = missionNamespace getVariable [QEGVAR(nightvision,nvgFlashUntil), -1];
    if !(_current isEqualType 0) then { _current = -1; };
    missionNamespace setVariable [QEGVAR(nightvision,nvgFlashUntil), _current max _until];
};

_f
