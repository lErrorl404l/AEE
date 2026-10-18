#include "..\..\script_component.hpp"
/*
Freezing rain and surface icing.

Freezing rain is the precipitation phase fnc_calculatePrecipitationPhase
resolves from the wet-bulb temperature: rain above a frozen surface
(aee_core_precipitationPhase "freezing_rain", published earlier in the
tick).  Its icing rate is the Jones (1998, CRREL Report 98-1) simple
flux model for a freezing-rain glaze on a cylinder in calm air:
  radial ice accretion = P rho_w / (pi rho_i)   (mm/h),  rho_i 900 kg/m3,
P the liquid precipitation rate (the engine level times ENGINE_RAIN_FULL_MMH).
The severity 0..1 is that accretion over one hour against the NWS ice-storm
warning criterion, 6.35 mm (0.25 in) of radial ice: 1 means warning-level
glaze within the hour.

Sets GVAR(currentFreezingRain)  - bool
Sets GVAR(currentIcingSeverity) - float 0-1
Sets GVAR(iceAccretionRate)     - radial ice, mm/h
*/
private _phase = missionNamespace getVariable [QEGVAR(core,precipitationPhase), "rain"];
if !(_phase isEqualType "") then { _phase = "rain"; };
private _isFreezing = _phase == "freezing_rain";
private _accretion = 0;
if (_isFreezing) then {
    private _pMmH = ((rain max 0) min 1) * ENGINE_RAIN_FULL_MMH;
    _accretion = _pMmH * 1000 / (pi * 900);
};
private _severity = (_accretion / 6.35) min 1;

missionNamespace setVariable [QEGVAR(core,currentFreezingRain), _isFreezing];
missionNamespace setVariable [QEGVAR(core,currentIcingSeverity), _severity];
missionNamespace setVariable [QEGVAR(core,iceAccretionRate), _accretion];
_isFreezing
