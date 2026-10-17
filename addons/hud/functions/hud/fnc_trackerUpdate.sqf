#include "..\..\script_component.hpp"
/*
 * aee_hud_fnc_trackerUpdate
 *
 * The signal-dependent tracker driver.  Once per survey interval it reads the
 * EXACT positions of the local group (units group player), finds the GPS
 * satellites each unit can see (the real constellation at the mission date,
 * blocked by terrain and structures along each line of sight), forms the fix,
 * its geometry and its time-correlated error, and publishes the per-track
 * state the draw layer renders:
 *
 *   aee_hud_trackerTracks     array of track records (see below)
 *   aee_hud_trackerR95        the largest error radius in the group, metres
 *   aee_hud_trackerFix        the worst fix quality in the group
 *   aee_hud_trackerOwn        the player's own receiver: [reported position
 *                             AGL, fix quality, R95 m]
 *   aee_hud_trackerPrev       per-unit fix state for the next survey
 *   aee_hud_trackerTime       diag_tickTime of the last survey
 *   aee_hud_trackerLogAt      diag_tickTime of the next log line
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
    missionNamespace setVariable [QGVAR(trackerOwn), nil];
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

// The GPS sky for this instant: the constellation of the GPS SPS PS (2020)
// at the mission date and time (fnc_gameClockToUT) over the map's location.
private _loc = [] call EFUNC(lib,getWorldLocation);
private _ut = [date, dayTime, _loc select 2] call EFUNC(lib,gameClockToUT);
private _sky = [_ut select 0, _ut select 1, _loc select 0, _loc select 2, -1] call EFUNC(lib,gnssSatellites);

// Range error: measured by geomagnetic latitude and scaled with the solar
// cycle (fnc_gnssUere), from the published space weather.
private _mlat = missionNamespace getVariable [QEGVAR(weather,geomagneticLatitude), 45];
if !(_mlat isEqualType 0) then { _mlat = 45; };
private _ssn = missionNamespace getVariable [QEGVAR(weather,sunspotNumber), 100];
if !(_ssn isEqualType 0) then { _ssn = 100; };
private _uere = [_mlat, _ssn] call EFUNC(lib,gnssUere);

// The datalink radio (CBA settings; defaults: L3Harris AN/PRC-152A data
// sheet, 5 W and -116 dBm) and the ATAK reporting rates (ATAK-CIV defaults
// for a multicast radio network: 30 s still, 20 s slow, 2 s fast).
private _txDbm = missionNamespace getVariable [QGVAR(trackerTxPowerDbm), 37];
private _gainDbi = missionNamespace getVariable [QGVAR(trackerAntennaGainDbi), 0];
private _sensDbm = missionNamespace getVariable [QGVAR(trackerRxSensitivityDbm), -116];
private _fMHz = missionNamespace getVariable [QGVAR(trackerFrequencyMHz), 100];
private _rateStill = missionNamespace getVariable [QGVAR(trackerReportStationary), 30];
private _rateSlow = missionNamespace getVariable [QGVAR(trackerReportSlow), 20];
private _rateFast = missionNamespace getVariable [QGVAR(trackerReportFast), 2];
private _excessDb = missionNamespace getVariable [QEGVAR(radio,excessLossDB), 0];
if !(_excessDb isEqualType 0) then { _excessDb = 0; };

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
    // [timeSinceFix, acquireRemaining, errorEN, receiver position, ellipse,
    //  shown report, last transmit time, last received time, speed and
    //  altitude at the last transmit, link state]
    private _prev = _previous getOrDefault [_netId, [0, 0, [], [], [], [], -1e9, _now, -1, -1e9, "received"]];
    _prev params ["_prevSince", "_prevAcquire", "_prevError", "_heldPos", "_prevEllipse",
        "_shownPrev", "_lastTx", "_lastRx", "_txSpeed", "_txAlt", "_linkState"];

    // A satellite is received when its line of sight is clear.  Terrain and
    // structures block L1; foliage only attenuates it (a 38 dB margin between
    // the -128.5 dBm minimum received power of IS-GPS-200 and the -167 dBm
    // tracking sensitivity of a u-blox M8), so vegetation does not block.
    private _ignore = vehicle _unit;
    private _visible = _sky select {
        private _dir = [_x select 0, _x select 1, _x select 2];
        private _far = _eye vectorAdd (_dir vectorMultiply 3000);
        private _near = _eye vectorAdd (_dir vectorMultiply 300);
        private _clear = !(terrainIntersectASL [_eye, _far]);
        if (_clear) then {
            private _hits = lineIntersectsSurfaces [_eye, _near, _unit, _ignore, true, 1, "GEOM", "NONE"];
            if ((count _hits) > 0) then {
                private _obj = (_hits select 0) select 2;
                if (isNull _obj) then {
                    _clear = false;
                } else {
                    private _model = toLowerANSI ((getModelInfo _obj) select 1);
                    _clear = ("plants" in _model) || ("vegetation" in _model);
                };
            };
        };
        _clear
    };
    private _count = count _visible;

    private _fixOut = [_dt, _count, [_prevSince, _prevAcquire]] call EFUNC(lib,gnssFixState);
    private _quality = _fixOut select 0;

    // Geometry: a 2D fix holds the height, the altitude constraint row.
    private _rows = +_visible;
    if (_count == 3) then { _rows pushBack [0, 0, 1, 0]; };
    private _ellipse = _prevEllipse;
    private _error = _prevError;
    if (_quality isNotEqualTo "none") then {
        _ellipse = [[_rows] call EFUNC(lib,gnssDop), _uere] call EFUNC(lib,gnssErrorEllipse);
        _error = [_prevError, _ellipse, _dt, random 1, random 1] call EFUNC(lib,gnssErrorStep);
    };
    if ((count _ellipse) < 9) then { _ellipse = [-1, -1, -1, 0, 0, 0, -1, -1, 0]; };

    // The receiver's own solution; with no fix it holds the last one.
    private _gpsPos = ([_exact, _ellipse, _quality, _error, _heldPos, 0] call FUNC(trackerProject)) select 0;

    // The unit sends its position on the ATAK dynamic schedule, and at once
    // on a 7 mph speed change or a 50 m climb (ATAK ReportingRate).  The
    // report reaches the player when the link budget closes over the
    // terrain between them; otherwise the last report is held and ages.
    private _speed = (speed (vehicle _unit)) / 3.6;
    private _interval = [_speed, _rateStill, _rateSlow, _rateFast] call FUNC(trackerReportInterval);
    private _shown = _shownPrev;
    if (_unit isEqualTo _player) then {
        _shown = _gpsPos;
        _lastRx = _now;
        _linkState = "received";
    } else {
        if (((_now - _lastTx) >= _interval) || {(abs (_speed - _txSpeed)) >= 3.12928} || {(abs ((_exact select 2) - _txAlt)) >= 50}) then {
            _lastTx = _now;
            _txSpeed = _speed;
            _txAlt = _exact select 2;
            private _dM = (_eye distance2D _playerEye) max 1;
            private _samples = ((ceil (_dM / 30)) min 64) max 2;
            private _dist = [];
            private _hgt = [];
            for "_k" from 1 to (_samples - 1) do {
                private _f = _k / _samples;
                _dist pushBack (_f * _dM / 1000);
                _hgt pushBack (getTerrainHeightASL (_eye vectorAdd ((_playerEye vectorDiff _eye) vectorMultiply _f)));
            };
            private _link = [_txDbm, _gainDbi, _sensDbm, _fMHz, _dM / 1000, _dist, _hgt,
                _eye select 2, _playerEye select 2, _excessDb] call EFUNC(lib,datalinkState);
            _linkState = _link select 0;
            if (_linkState isEqualTo "received") then {
                _shown = _gpsPos;
                _lastRx = _now;
            };
        };
    };
    if ((count _shown) < 3) then { _shown = _gpsPos; };
    private _age = (_now - _lastRx) max 0;

    _next set [_netId, [_fixOut select 1, _fixOut select 2, _error, _gpsPos, _ellipse,
        _shown, _lastTx, _lastRx, _txSpeed, _txAlt, _linkState]];

    _tracks pushBack [_unit, _exact, _shown, _ellipse, _age, _quality, _linkState, _suppress];

    if (_unit isEqualTo _player) then {
        missionNamespace setVariable [QGVAR(trackerOwn), [ASLToAGL _gpsPos, _quality, _ellipse select 7]];
    };
    if ((_ellipse select 7) > _maxR95) then { _maxR95 = _ellipse select 7; };
    if (_quality isEqualTo "none") then {
        _worst = "none";
    } else {
        if ((_quality isEqualTo "degraded") && (_worst isNotEqualTo "none")) then {
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
