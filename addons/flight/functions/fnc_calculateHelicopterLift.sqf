#include "..\script_component.hpp"

/*
Helicopter lift density ratio — current air density relative to ISA sea-level
(AERO_ISA_SEA_LEVEL_DENSITY kg/m³ at 15 °C).

  ratio = 1.0  — equivalent to sea-level standard-day performance
  ratio < 1.0  — reduced lift (hot day, high altitude, or both)
  ratio > 1.0  — enhanced lift (cold dense air)

Reads the pre-computed air density from GVAR(currentAirDensity).  When that
is not available (fallback) it estimates density from elevation using a
standard-atmosphere exponential approximation.

Stored in GVAR(currentLiftRatio).
*/

private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), -1];

if (_density <= 0) then {
    // Fallback — standard atmosphere exponential
    private _elevation = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
    if !(_elevation isEqualType 0) then { _elevation = 0; };
    if (_elevation <= 0) then {
        private _player = call CBA_fnc_currentUnit;
        if (isNull _player) then {
            _elevation = 0;
        } else {
            _elevation = getTerrainHeightASL (getPos _player);
        };
    };
    _density = AERO_ISA_SEA_LEVEL_DENSITY * exp (-_elevation / 8500);
};

private _ratio = _density / AERO_ISA_SEA_LEVEL_DENSITY;
_ratio = _ratio max 0.4 min 1.05;

missionNamespace setVariable [QGVAR(currentLiftRatio), _ratio];
