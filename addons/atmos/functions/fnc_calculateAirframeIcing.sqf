#include "..\script_component.hpp"

/*
Airframe icing severity (0–1) for aircraft in supercooled liquid water.

Icing risk exists when flying through visible moisture (cloud or
precipitation) at temperatures between -20 °C and 0 °C.  Severity
scales with moisture content and peaks between -5 °C and -10 °C.

Stored in GVAR(airframeIcing) and GVAR(airframeIcingDetected).
*/

private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _overcast = overcast;
private _rain = rain;

// ─── Temperature range check — no risk outside -20..0 ──────────────────
private _severity = 0;

if (_temp > -20 && _temp < 0) then {
    // ─── Cloud moisture contribution ────────────────────────────────────
    if (_overcast > 0.5) then {
        _severity = _severity + (_overcast - 0.5) * 2 * 0.6;
    };

    // ─── Precipitation moisture contribution ────────────────────────────
    if (_rain > 0) then {
        _severity = _severity + _rain * 2 * 0.8;
    };

    // ─── Peak icing sweet spot (-5 to -10 °C) ──────────────────────────
    if (_temp > -10 && _temp < -5) then {
        _severity = _severity * 1.3;
    };
};

_severity = _severity max 0 min 1;

private _detected = _severity > 0.01;

missionNamespace setVariable [QGVAR(airframeIcing), _severity];
missionNamespace setVariable [QGVAR(airframeIcingDetected), _detected];

_severity
