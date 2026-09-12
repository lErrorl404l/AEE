#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes atmospheric haze from relative humidity and dust suppression. Haze is aerosol scattering below saturation. Fog is condensation at saturation. Aerosols grow hygroscopically before condensation. The growth follows the Köhler curve. Dust suppression removes haze.
Arguments: None
Return Value: NUMBER: haze 0..1
Example: [] call aee_atmos_fnc_calculateHaze
Public: No
*/

private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _dustSuppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0];

// ─── Aerosol growth ──────────────────────────────────────────────────────
// Below 40 % RH the air holds little aerosol water. From 40 % to
// saturation the aerosols swell, which increases scattering. This linear
// branch is a proxy for the Köhler growth curve.
private _haze = 0;
if (_humidity >= 40) then {
    _haze = 0.2 + 0.8 * ((_humidity - 40) / 60);
};

// ─── Fog scavenging ──────────────────────────────────────────────────────
// At saturation fog droplets form and settle the haze particles.
if (_humidity >= 99.5) then { _haze = _haze * 0.3; };

// ─── Dust suppression ────────────────────────────────────────────────────
_haze = _haze - (_dustSuppression * 0.15);
_haze = _haze max 0 min 1;

missionNamespace setVariable [QEGVAR(core,currentHaze), _haze];

_haze
