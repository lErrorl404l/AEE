#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_trackerUpdate
 *
 * The signal-dependent tracker driver.  Once per survey interval it reads the
 * EXACT positions of the local group (units group player), applies the three
 * aee GNSS kernels, and publishes the per-track state the draw layer renders:
 *
 *   aee_optics_trackerTracks     array of track records (see below)
 *   aee_optics_trackerR95        the largest error radius in the group, metres
 *   aee_optics_trackerFix        the worst fix quality in the group
 *   aee_optics_trackerPrev       per-unit fix state for the next survey
 *   aee_optics_trackerTime       diag_tickTime of the last survey
 *   aee_optics_trackerLogAt      diag_tickTime of the next log line
 *
 * Track record: [unit, exactPos, displayedPos, ellipse, trackAge, quality,
 *                linkState, suppressed]
 *
 * The tracker is CLIENT-LOCAL.  It never broadcasts the tracker state over the
 * network and it writes no other module's state; it reads the published aee
 * state and the engine.
 *
 * ── Engine icon suppression probe (recorded capability) ───────────────────
 * The engine draws its own friendly unit map markers.  The probe result:
 *
 *   ALLOWED:  disableMapIndicators [disableFriendly, disableEnemy,
 *             disableMines, disablePing] (Arma 3 1.82+, Difficulty group,
 *             LOCAL effect).  With the first element true it suppresses the
 *             engine friendly map indicators, but only when the difficulty
 *             setting exposes "extended map content".  The effect is LOCAL, it
 *             resets on a difficulty change and on respawn or teamSwitch, so
 *             this driver re-applies it every survey.
 *   NOT ALLOWED: setGroupIconsVisible [showOnMap, showOnHUD] affects ONLY the
 *             icons added with addGroupIcon (High Command).  It does NOT hide
 *             the default engine unit or group markers, so it is not used here.
 *             No config surface repoints the vanilla GPS readout either.
 *
 * The probe result is logged once per window through AEE_LOG_DEBUG and is
 * reported in the task-13 evidence.  The visible result is operator-only.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _enabled = missionNamespace getVariable [QGVAR(trackerEnabled), false];
if !(_enabled isEqualType true) then { _enabled = false; };
if (!_enabled) exitWith {
    missionNamespace setVariable [QGVAR(trackerTracks), []];
};

private _interval = missionNamespace getVariable [QGVAR(trackerInterval), 1.0];
if !(_interval isEqualType 0) then { _interval = 1.0; };
_interval = (_interval) max 0.2;

private _now = diag_tickTime;
private _last = missionNamespace getVariable [QGVAR(trackerTime), -1e9];
if !(_last isEqualType 0) then { _last = -1e9; };
if ((_now - _last) < _interval) exitWith {};
missionNamespace setVariable [QGVAR(trackerTime), _now];

private _dt = ((_now - _last) max 0.01) min 30;

// ── Engine icon suppression probe ─────────────────────────────────────────
// Apply the LOCAL suppression when the operator asks for it.  The call is
// harmless where the difficulty does not expose extended map content; there
// the engine markers simply remain.  This is the honest ceiling.
private _suppress = missionNamespace getVariable [QGVAR(trackerSuppressIcons), false];
if !(_suppress isEqualType true) then { _suppress = false; };
private _suppressWas = missionNamespace getVariable [QGVAR(trackerIndicatorsSuppressed), false];
if !(_suppressWas isEqualType true) then { _suppressWas = false; };
if (_suppress) then {
    disableMapIndicators [true, false, false, false];
} else {
    // The suppression is a persistent LOCAL effect, so it must be reversed
    // when the operator turns the setting off, or the engine indicators stay
    // hidden for the rest of the session.
    if (_suppressWas) then {
        disableMapIndicators [false, false, false, false];
    };
};
missionNamespace setVariable [QGVAR(trackerIndicatorsSuppressed), _suppress];

private _player = call CBA_fnc_currentUnit;
private _units = units (group _player);
private _previous = missionNamespace getVariable [QGVAR(trackerPrev), createHashMap];

// The atmospheric index comes from the published aee humidity (0 to 100).
// The mapping is UNSOURCED.
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_humidity isEqualType 0) then { _humidity = 50; };
private _atmosIndex = ((_humidity / 100) max 0) min 1;

private _playerEye = eyePos _player;
private _tracks = [];
private _next = createHashMap;
private _maxR95 = 0;
private _worst = "ok";

for "_i" from 0 to ((count _units) - 1) do {
    private _unit = _units select _i;
    private _exact = getPosASL _unit;
    private _eye = eyePos _unit;
    private _netId = netId _unit;
    private _prevState = _previous getOrDefault [_netId, [0, 1]];

    // Canopy: a blocked vertical ray means the sky is occluded.  UNSOURCED.
    private _canopy = 0;
    if (lineIntersects [_eye, [_eye select 0, _eye select 1, (_eye select 2) + 40], _unit]) then {
        _canopy = 1;
    };

    // Urban: buildings within the survey radius, saturating at the cap.
    // UNSOURCED.
    private _buildings = count (nearestTerrainObjects [getPosATL _unit, ["Building"], 50]);
    private _urban = ((_buildings / 8) max 0) min 1;

    // Terrain mask between the player and the track.  UNSOURCED.
    private _terrain = 0;
    if (lineIntersects [_playerEye, _eye, _player, _unit]) then {
        _terrain = 1;
    };

    private _distance = _player distance _unit;

    // Signal quality falls with canopy and urban cover.  UNSOURCED.
    private _signal = ((1 - (0.5 * _canopy) - (0.3 * _urban)) max 0) min 1;

    // The kernels are called with every argument explicit; a nested call does
    // not evaluate the kernel defaults.
    private _fixOut = [_dt, _signal, 0, _prevState] call EFUNC(lib,gnssFixState);
    private _ellipse = [
        1.0,      // DOP: nominal geometry, UNSOURCED
        3.6,      // UERE: GPS SPS PS 5th ed, 3.6 m RMS
        _atmosIndex,
        _canopy,
        _urban,
        0,        // jamming: no jammer source is published
        1.0       // receiver quality: nominal, UNSOURCED
    ] call EFUNC(lib,gnssErrorEllipse);
    private _linkOut = [
        _distance,
        _terrain,
        _urban,
        0,        // jammer state
        100       // bandwidth: the kernel reference, UNSOURCED
    ] call EFUNC(lib,datalinkState);

    private _seed = (((_i % 7) + 1) / 7);
    private _projected = [_exact, _ellipse, _fixOut, _linkOut, _seed] call FUNC(trackerProject);

    _next set [_netId, [_fixOut select 1, _fixOut select 2]];

    private _trackRecord = [
        _unit,
        _exact,
        _projected select 0,
        _ellipse,
        _projected select 4,
        _fixOut select 0,
        _linkOut select 0,
        _suppress
    ];
    _tracks pushBack _trackRecord;

    if ((_ellipse select 7) > _maxR95) then { _maxR95 = _ellipse select 7; };
    if ((_fixOut select 0) isEqualTo "none") then {
        _worst = "none";
    } else {
        if (((_fixOut select 0) isEqualTo "degraded") && (_worst isNotEqualTo "none")) then {
            _worst = "degraded";
        };
    };
};

missionNamespace setVariable [QGVAR(trackerPrev), _next];
missionNamespace setVariable [QGVAR(trackerTracks), _tracks];
missionNamespace setVariable [QGVAR(trackerR95), _maxR95];
missionNamespace setVariable [QGVAR(trackerFix), _worst];

// One trace line per window, through the module switch, so the tracker can be
// read in an .rpt without a per-frame cost.  It records the suppression
// capability too.
private _logAt = missionNamespace getVariable [QGVAR(trackerLogAt), -1e9];
if !(_logAt isEqualType 0) then { _logAt = -1e9; };
if (_now >= _logAt) then {
    missionNamespace setVariable [QGVAR(trackerLogAt), _now + 5];
    private _logMsg = format [
        "tracker update: tracks=%1 worst=%2 r95=%3 suppress=%4 (disableMapIndicators LOCAL; setGroupIconsVisible cannot hide the engine markers)",
        count _tracks, _worst, round _maxR95, _suppress
    ];
    AEE_LOG_DEBUG(_logMsg);
};
