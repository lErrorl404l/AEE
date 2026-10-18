#include "..\..\script_component.hpp"

/*
AEE to engine weather writer (issue #155).

Maps AEE's modelled atmosphere onto the engine's own weather commands so a
modelled storm shows in the engine: cloud, rain, a wet surface and the
engine's wind response to a raised overcast.

ENGINE CONTRACT (local command DB, acemod/arma3-wiki v2.22; each command's
commands/<name>.yml, the column-0 `since` block):

  time setOvercast value    overcast 0..1          Local        Arma 3 0.50
  time setRain value        rain 0..1              Global       Arma 3 0.50
  setHumidity value         surface humidity 0..1  Local        Arma 3 2.8
  forceWeatherChange        nular                  Unspecified  Arma 3 1.16

Locality: `setOvercast` and `setRain` propagate globally ONLY when the
SERVER calls them; a client call is local and temporary and reverts to the
server value (command DB `setRain`).  `setHumidity` has no global form, so it
runs once per client.  Engine coupling: rain does not fall below overcast 0.5
in Arma 3 (command DB `setRain`), so the modelled rain is gated on the
modelled overcast.

PRECEDENCE is FUNC(engineWeatherBlockedReason): two gates, first match wins,
the setting, then the operator's manual-weather gate.  AEE alone owns the
engine weather, so no third gate exists.

INTERPOLATION: every value uses the engine's timed form,
`<interval> setOvercast value` and `<interval> setRain value`, so the engine
ramps over one AEE tick instead of snapping.

forceWeatherChange is NOT called on this per-tick path: it skips the smooth
transition and can cause lag (command DB `forceWeatherChange`).  It is
reserved for an explicit transition, requested once by a caller that passes
_force = true.

WIND is not written here.  FUNC(updateWind) is the single owner of the engine
wind vector (`setWind [x, y, false]`); a second writer would feed back through
that per-tick read and compound (ADR-041).  The engine raises wind with
overcast, so the overcast write below is the only wind lever this writer
holds.

Reads:  aee_core_currentHumidity, aee_core_orographicFactor,
        aee_atmos_frontPrecipRate, aee_atmos_frontCloudTerm,
        aee_core_updateInterval
Sets:   aee_atmos_engineWeatherBlocked, aee_atmos_overcastBaseline,
        aee_atmos_targetOvercast, aee_atmos_targetRain,
        engine overcast + rain (server), engine surface humidity (client)

Arguments:
  0: force an immediate transition (Boolean, optional, default false)
Public: No
*/

params [["_force", false, [false]]];

// ─── Precedence ─────────────────────────────────────────────────────────────
private _reason = call FUNC(engineWeatherBlockedReason);
missionNamespace setVariable [QGVAR(engineWeatherBlocked), _reason];

if (_reason != "") exitWith {
    private _skipMsg = format ["Engine weather write skipped: %1", _reason];
    AEE_LOG_DEBUG(_skipMsg);
};

private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
if !(_interval isEqualType 0) then { _interval = 5; };
_interval = _interval max 1;

// ─── Surface humidity (client; the engine command has no global form) ───────
// `setHumidity` is Local and has only the unary form (command DB).  Its 0..1
// scale is the same 0..1 the `humidity` getter reports as 100 % RH, so the
// modelled relative humidity in percent maps by dividing by 100.
if (hasInterface) then {
    private _rhPct = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
    if !(_rhPct isEqualType 0) then { _rhPct = 50; };
    setHumidity ((_rhPct / 100) max 0 min 1);
};

if (!isServer) exitWith {};

// ─── Modelled overcast fraction (0..1) ──────────────────────────────────────
// AEE holds its own absolute cloud fraction.  It is seeded ONCE from the
// engine overcast so an authored mission sky is the floor, then driven by
// AEE's humidity and front models.  Holding the value in AEE state is what
// keeps the writer from reading back its own engine write and compounding.
private _baseline = missionNamespace getVariable [QGVAR(overcastBaseline), -1];
if (!(_baseline isEqualType 0) || _baseline < 0) then {
    _baseline = overcast;
    if !(_baseline isEqualType 0) then { _baseline = 0; };
    _baseline = _baseline max 0 min 1;
    missionNamespace setVariable [QGVAR(overcastBaseline), _baseline];
};

// Cloud cover from relative humidity, the Sundqvist diagnostic cloud fraction
// (Sundqvist 1978; Sundqvist, Berge and Kristjansson 1989, Mon. Wea. Rev.
// 117:1641) as the Eta model runs it:
//   C = 1 - sqrt((1 - RH) / (1 - U00)),  RH > U00,
// with the near-surface critical humidity U00 = 0.95 (the Eta scheme, falling
// to 0.75-0.80 aloft; Eta cloud parameterization, SANU monograph).  The input
// is the surface humidity, so the surface value applies.  The engine
// overcast is the cloud fraction.
private _rhFrac = (missionNamespace getVariable [QEGVAR(core,currentHumidity), 50]) / 100;
if !(_rhFrac isEqualType 0) then { _rhFrac = 0.5; };
_rhFrac = (_rhFrac max 0) min 1;
private _rhCloud = 0;
if (_rhFrac > 0.95) then { _rhCloud = 1 - sqrt ((1 - _rhFrac) / (1 - 0.95)); };

// The front model supplies the cloud forcing: building ahead of the front,
// clearing behind it (aee_atmos_frontCloudTerm, signed).
private _frontCloud = missionNamespace getVariable [QGVAR(frontCloudTerm), 0];
if !(_frontCloud isEqualType 0) then { _frontCloud = 0; };

private _targetOvercast = (((_baseline max _rhCloud) + _frontCloud) max 0) min 1;

// ─── Modelled precipitation intensity (mm/h to engine 0..1) ─────────────────
// aee_atmos_frontPrecipRate is the intrinsic frontal rate in millimetres per
// hour (fnc_updateWeatherFront).  The orographic factor scales it for a ridge.
private _orographic = missionNamespace getVariable [QEGVAR(core,orographicFactor), 1];
if !(_orographic isEqualType 0) then { _orographic = 1; };
private _rateMmH = missionNamespace getVariable [QGVAR(frontPrecipRate), 0];
if !(_rateMmH isEqualType 0) then { _rateMmH = 0; };
_rateMmH = (_rateMmH * _orographic) max 0;

// ONE documented conversion: the engine rain value is the modelled rate in
// mm/h divided by ENGINE_RAIN_FULL_MMH (the mm/h the engine renders as rain
// 1.0, addons/lib/constants.hpp).  The modelled mm/h and the engine 0..1 stay
// separate; this line is the only place the two meet.
private _targetRain = (_rateMmH / ENGINE_RAIN_FULL_MMH) max 0 min 1;

// Engine coupling: rain does not fall below overcast 0.5 in Arma 3 (command
// DB `setRain`).  Precipitation implies a cloudy sky, so raise the target
// overcast to the floor before suppressing the rain below it.
if (_targetRain > 0 && _targetOvercast < 0.5) then { _targetOvercast = 0.5; };
if (_targetOvercast < 0.5) then { _targetRain = 0; };

missionNamespace setVariable [QGVAR(targetOvercast), _targetOvercast];
missionNamespace setVariable [QGVAR(targetRain), _targetRain];

// ─── Engine write (timed form; server authority) ────────────────────────────
// The force request is an explicit transition: apply it at once and ask the
// engine to skip the interpolation.  Otherwise ramp over one AEE tick.
private _transition = [_interval, 0] select _force;

private _writeMsg = format ["Engine weather write: overcast %1, rain %2 over %3 s",
    round (_targetOvercast * 100) / 100, round (_targetRain * 100) / 100, _transition];
AEE_LOG_DEBUG(_writeMsg);

_transition setOvercast _targetOvercast;
_transition setRain _targetRain;

if (_force) then {
    forceWeatherChange;
};
