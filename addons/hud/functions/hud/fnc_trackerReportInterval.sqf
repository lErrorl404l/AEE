#include "..\..\script_component.hpp"
/*
 * aee_hud_fnc_trackerReportInterval
 *
 * Seconds between self position reports, the ATAK "Dynamic" reporting
 * strategy (ATAK-CIV, com.atakmap.comms.ReportingRate.checkIfTimeToReport).
 * Pure.
 *
 *   speed < 0.44704 m/s (1 mph)    the stationary interval
 *   speed >= 13.4112 m/s (30 mph)  the fast interval
 *   between: s' = 0.44704 + 100 (v - 0.44704) / (13.4112 - 0.44704)
 *            interval = slow - s' (slow - fast) / 100
 * (reproduced as ATAK computes it).  ATAK's defaults for an unreliable
 * (multicast radio) network: stationary 30 s, slow 20 s, fast 2 s.
 *
 * Arguments:
 *   0: speed      <NUMBER> m/s
 *   1: stationary <NUMBER> s
 *   2: slow       <NUMBER> s
 *   3: fast       <NUMBER> s
 * Return: seconds
 */
params [["_speed", 0, [0]], ["_stationary", 30, [0]], ["_slow", 20, [0]], ["_fast", 2, [0]]];
private _vMin = 0.44704;
private _vMax = 13.4112;
if (_speed < _vMin) exitWith { _stationary };
if (_speed >= _vMax) exitWith { _fast };
private _scaled = _vMin + (((_speed - _vMin) * 100) / (_vMax - _vMin));
_slow - ((_scaled * (_slow - _fast)) / 100)
