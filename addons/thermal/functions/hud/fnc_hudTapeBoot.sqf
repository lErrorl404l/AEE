#include "..\..\script_component.hpp"
/*
 * Fusion HUD power-on / power-off animation (issue #204).
 *
 * Imitates the power-up and power-down of a real ECOTI / image-intensified
 * tube.  Runs every frame from the Draw3D worker.  The source (workshop
 * 3810296503 whale_ecoti_llll functions/fn_boot.sqf) does two things: it drives
 * a brightness envelope and it raises or lowers the overlay.  This function
 * owns both, so the display lifetime has one owner.
 *
 * The animation only changes brightness, never size.  The envelope flashes the
 * glass and the tape twice (t about 0.10 s and 0.40 s) and, on power-on, fades
 * the glass in over the first 35 percent, the ruler in over 5 to 80 percent and
 * the corner readouts in over 25 to 95 percent.  Power-off reverses all three.
 * The profile is published as
 *   QGVAR(hudTapeBootProfile) = [hudK, glassA, infoK, glassBoost]
 * and read by FUNC(hudTapeDraw) (index 0) and FUNC(hudTapeInfo) (index 2).
 *
 * State: QGVAR(hudTapeAnim) 0 none / 1 powering on / 2 powering off,
 *        QGVAR(hudTapeAnimStart) animation start time.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _anim = missionNamespace getVariable [QGVAR(hudTapeAnim), 0];
if !(_anim isEqualType 0) then { _anim = 0; };
private _raised = missionNamespace getVariable [QGVAR(hudTapeOn), false];
if !(_raised isEqualType true) then { _raised = false; };

// Edge on: raise the display and start the power-on envelope.  Edge off: start
// the power-off envelope; the display stays up until that envelope finishes.
private _active = [] call FUNC(hudTapeActive);
if (_active && {!_raised}) then {
    [true] call FUNC(hudTapeBuild);
    _raised = true;
    _anim = 1;
    missionNamespace setVariable [QGVAR(hudTapeAnim), 1];
    missionNamespace setVariable [QGVAR(hudTapeAnimStart), time];
};
if (!_active && _raised && (_anim == 0)) then {
    _anim = 2;
    missionNamespace setVariable [QGVAR(hudTapeAnim), 2];
    missionNamespace setVariable [QGVAR(hudTapeAnimStart), time];
};

private _glassA = 1;
private _glassBoost = 0;
private _hudK = 1;
private _infoK = 1;
private _done = false;

private _t0 = missionNamespace getVariable [QGVAR(hudTapeAnimStart), -1];
if !(_t0 isEqualType 0) then { _t0 = -1; };

if (_t0 >= 0) then {
    private _el = time - _t0;

    // The two flash peaks.  Each is a spike at its centre time that decays to
    // zero over its half-width.
    private _flick = 0;
    {
        private _d = abs (_el - (_x select 0));
        if (_d < (_x select 1)) then {
            private _v = (1 - _d / (_x select 1)) ^ 0.55;
            if (_v > _flick) then { _flick = _v; };
        };
    } forEach [[0.10, 0.14], [0.40, 0.14]];

    if (_anim == 1) then {
        private _dur = FUSION_HUD_BOOT_ON;
        if (_el >= _dur) then {
            missionNamespace setVariable [QGVAR(hudTapeAnim), 0];
            missionNamespace setVariable [QGVAR(hudTapeAnimStart), -1];
        } else {
            private _p = _el / _dur;
            _glassA = (_p / 0.35) min 1;
            private _h = (((_p - 0.05) / 0.75) max 0) min 1;
            _hudK = 1 - (1 - _h) * (1 - _h);
            _infoK = (((_p - 0.25) / 0.70) max 0) min 1;
            _glassBoost = _flick;
            _hudK = (_hudK max _flick);
            _infoK = (_infoK max _flick);
        };
    } else {
        if (_anim == 2) then {
            private _dur = FUSION_HUD_BOOT_OFF;
            if (_el >= _dur) then {
                _done = true;
            } else {
                private _q = _el / _dur;
                _glassA = ((1 - _q) ^ 1.4);
                _hudK = ((1 - _q) ^ 1.2);
                _infoK = (((1 - _q * 1.5) max 0) min 1);
                private _fk = _flick * (1 - _q);
                _glassBoost = _fk;
                _hudK = (_hudK max _fk);
                _infoK = (_infoK max _fk);
            };
        };
    };
};

missionNamespace setVariable [QGVAR(hudTapeBootProfile), [_hudK, _glassA, _infoK, _glassBoost]];

// Power-off finished: lower the display and reset the profile.
if (_done) then {
    [false] call FUNC(hudTapeBuild);
    _raised = false;
    missionNamespace setVariable [QGVAR(hudTapeAnim), 0];
    missionNamespace setVariable [QGVAR(hudTapeAnimStart), -1];
    missionNamespace setVariable [QGVAR(hudTapeBootProfile), [1, 1, 1, 0]];
};

// Drive the glass.  The display is created on the cut frame, so place it the
// first frame the handle is live rather than assuming the config onLoad ran
// before this worker.
private _disp = uiNamespace getVariable [QGVAR(fusionHudDisplay), displayNull];
if (!isNull _disp && _raised) then {
    private _ready = missionNamespace getVariable [QGVAR(hudTapeGlassReady), false];
    if !(_ready isEqualType true) then { _ready = false; };
    if (!_ready) then {
        [_disp] call FUNC(hudTapeOnLoad);
    };
    private _g = _disp displayCtrl 910001;
    if (!isNull _g) then {
        private _c = FUSION_HUD_GLASS_COLOR;
        private _b = 1 + 1.2 * _glassBoost;
        _g ctrlSetBackgroundColor [
            (((_c select 0) * _b) min 1),
            (((_c select 1) * _b) min 1),
            (((_c select 2) * _b) min 1),
            ((((_c select 3) * _glassA) + 0.22 * _glassBoost) min 0.75)
        ];
        _g ctrlCommit 0;
    };
};
