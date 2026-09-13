#include "..\script_component.hpp"

/*
 * Shared illuminance layer — the single source of light data for every
 * module (NVG, thermal, glare, ballistics visibility).
 *
 * PRIMARY: getLighting (no-arg).  Returns [ambientColor, ambientBrightness,
 * lightDirection, starsVisibility].  Verified on a dedicated server (docker
 * probe): 4 elements, works headless.  lightDirection is the sun/moon
 * vector — the glare/thermal source.  ambientBrightness is FROZEN on a
 * headless server (the lighting engine only advances per-camera), so it
 * is NOT used as the lux source.
 *
 * LUX SOURCE: the validated moonIntensity/overcast/rain model (real engine
 * variables, time-varying on every machine).  Engine illuminance cannot
 * be sampled at night without a client camera (getLightingAt returns []
 * on a logic, frozen on headless, and is client-NV-dependent per tracker
 * T156930), so the physics lux model remains authoritative.
 *
 * DYNAMIC: getLightingAt needs a real UNIT (returns [] on a logic).  It
 * adds dynamic light-source lux on the client; skipped on the server.
 *
 * Outputs (missionNamespace, shared):
 *   aee_core_illuminanceLux     - total lux (moon model + client dynamic)
 *   aee_core_ambientLux         - ambient lux (moon model)
 *   aee_core_dynamicLux         - dynamic (light-source) lux, client only
 *   aee_core_lightDirection     - engine sun/moon unit vector (getLighting)
 *   aee_core_lightAzimuth       - compass azimuth of primary light, degrees
 *   aee_core_lightElevation     - elevation of primary light, degrees
 *   aee_core_lightIsNight       - true when the engine reports no sun
 *   aee_core_starsVisibility    - engine star visibility 0..1
 */

params [["_posASL", [0, 0, 0], [[]]]];

// ─── Primary: getLighting direction + stars (works everywhere) ───────────
private _lightDir = [0, 0, 1];
private _stars = 0;
private _lightGlobal = getLighting;
if (count _lightGlobal >= 4) then {
    private _dir = _lightGlobal select 2;
    _stars = _lightGlobal select 3;
    if (_dir isEqualType [] && {count _dir == 3}) then { _lightDir = _dir; };
};

// Convert the engine's sun/moon vector to azimuth/elevation (degrees).
// Arma's light direction is a world vector pointing FROM the light: x=east,
// y=south, z=up (Arma compass convention: north = -y).  Azimuth is measured
// clockwise from north (getDir convention).  Elevation is angle above
// horizon, 0 at horizon, 90 straight up.
private _lightAzimuth = 0;
private _lightElevation = 0;
private _lightLen = vectorMagnitude _lightDir;
if (_lightLen > 0.001) then {
    _lightElevation = asin ((_lightDir select 2) / _lightLen);
    private _flatX = _lightDir select 0;
    private _flatY = _lightDir select 1;
    private _flatLen = sqrt ((_flatX * _flatX) + (_flatY * _flatY));
    if (_flatLen > 0.001) then {
        // atan2-like: north (0, -1) → 0°, east (1, 0) → 90°
        private _ang = _flatX atan2 (-_flatY);
        _lightAzimuth = _ang mod 360;
        if (_lightAzimuth < 0) then { _lightAzimuth = _lightAzimuth + 360; };
    };
};

// ─── Lux: validated moonIntensity/overcast/rain model ────────────────────
// Engine ambient brightness is frozen on headless and camera-dependent, so
// the lux base comes from real engine weather variables (moonIntensity,
// overcast, rain) — time-varying and identical on every machine.
private _moonLight = 0 max (moonIntensity - ((overcast * 0.8) min 0.275) - (rain * 0.5));
private _ambientLux = 0.001 + _moonLight * 0.249;

// ─── Dynamic: getLightingAt on the unit (client only) ────────────────────
// Returns [] on a logic; needs a real unit.  On a dedicated server it is
// frozen/none; the dynamic term is skipped there.
private _dynamicLux = 0;
private _unit = call CBA_fnc_currentUnit;
if (!isNull _unit && {hasInterface}) then {
    private _lightAt = getLightingAt _unit;
    if (count _lightAt >= 4) then {
        private _dynamicBright = _lightAt select 3;
        if (_dynamicBright isEqualType 0) then {
            _dynamicLux = (_dynamicBright max 0) * 100;
        };
    };
};

private _totalLux = _ambientLux + _dynamicLux;

// ─── Night detection ──────────────────────────────────────────────────────
// sunOrMoon: 1 = sun up, 0 = night.  Use it as the authoritative flag.
private _isNight = (sunOrMoon == 0);

missionNamespace setVariable [QGVAR(illuminanceLux), _totalLux];
missionNamespace setVariable [QGVAR(ambientLux), _ambientLux];
missionNamespace setVariable [QGVAR(dynamicLux), _dynamicLux];
missionNamespace setVariable [QGVAR(lightDirection), _lightDir];
missionNamespace setVariable [QGVAR(lightAzimuth), _lightAzimuth];
missionNamespace setVariable [QGVAR(lightElevation), _lightElevation];
missionNamespace setVariable [QGVAR(lightIsNight), _isNight];
missionNamespace setVariable [QGVAR(starsVisibility), _stars];

_totalLux
