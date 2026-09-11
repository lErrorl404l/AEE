#include "..\script_component.hpp"

/*
Helicopter lift density ratio — current air density relative to ISA sea-level
(1.225 kg/m³ at 15 °C).

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
    private _elevation = EGVAR(core,referenceAltitude);
    if (isNil "_elevation" || (_elevation <= 0)) then {
        private _player = call CBA_fnc_currentUnit;
        if (isNil "_player") then {
            _elevation = 0;
        } else {
            _elevation = getTerrainHeightASL (getPos _player);
        };
    };
    _density = 1.225 * exp (-_elevation / 8500);
};

private _ratio = _density / 1.225;
_ratio = _ratio max 0.4 min 1.05;

missionNamespace setVariable [QGVAR(currentLiftRatio), _ratio];
