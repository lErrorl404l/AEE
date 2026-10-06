#include "..\..\script_component.hpp"
/*
 * aee_core_fnc_datalinkState
 *
 * Pure, argument-driven datalink kernel.  It reads no world, no config, no
 * player and no radio module.  It models the range falloff, the terrain and
 * urban obstruction and the jamming of a tactical datalink, and it returns
 * the link state, the update interval, the track age and the added position
 * error.
 *
 * Propagation shape: the Friis free-space path loss
 *   FSPL = 20*log10(d) + 20*log10(f) - 147.55
 * the shape used by addons/radio/functions/fnc_calculateRadioPropagation.sqf.
 * This kernel reuses the SHAPE only.  It does not call the radio module and
 * it reads no mission variable.
 *
 * UNSOURCED shapes (listed for the per-constant register):
 *   DATA_REF_RANGE_M    nominal clear-air link range
 *   DATA_FREQ_HZ        reference carrier frequency
 *   DATA_TERRAIN_RANGE  usable-range fraction lost to full terrain masking
 *   DATA_URBAN_RANGE    usable-range fraction lost to full urban masking
 *   DATA_JAM_RANGE      usable-range fraction lost to full jamming
 *   DATA_TERRAIN_DB     signal loss at full terrain masking
 *   DATA_URBAN_DB       signal loss at full urban masking
 *   DATA_JAM_DB         signal loss at full jamming
 *   DATA_BASE_INTERVAL  update interval at reference signal and bandwidth
 *   DATA_REF_BANDWIDTH  reference bandwidth
 *   DATA_TRACK_AGE_MAX  track age at zero signal
 *   DATA_ERROR_MAX      added position error at zero signal
 *   DATA_ERROR_LOST     added position error penalty when the link is lost
 *
 * Arguments:
 *   0: distance    <NUMBER> link range, metres
 *   1: terrainMask <NUMBER> terrain obstruction, 0 clear to 1 blocked
 *   2: urbanMask   <NUMBER> urban obstruction, 0 clear to 1 blocked
 *   3: jammerState <NUMBER> jammer strength, 0 none to 1 full
 *   4: bandwidth   <NUMBER> link bandwidth, arbitrary units
 *
 * Return: [state, updateInterval, trackAge, addedPositionError]
 *   state is "received" or "lost".  updateInterval is seconds (0 when lost).
 *   trackAge is seconds.  addedPositionError is metres.
 */
params [
    ["_distance", 0, [0]],
    ["_terrainMask", 0, [0]],
    ["_urbanMask", 0, [0]],
    ["_jammerState", 0, [0]],
    ["_bandwidth", 0, [0]]
];

private _dist = _distance max 0;
private _terrain = ((_terrainMask) max 0) min 1;
private _urban = ((_urbanMask) max 0) min 1;
private _jammer = ((_jammerState) max 0) min 1;
private _bw = _bandwidth max 1;

// Range falloff.  Full masking shrinks the usable range.  All UNSOURCED.
private _refRange = 5000;                                // UNSOURCED
private _terrainRange = 0.6;                             // UNSOURCED
private _urbanRange = 0.3;                               // UNSOURCED
private _jamRange = 0.9;                                 // UNSOURCED
private _rangeLoss = (_terrain * _terrainRange) + (_urban * _urbanRange) + (_jammer * _jamRange);
private _effectiveRange = _refRange * ((1 - _rangeLoss) max 0);

private _received = (_dist <= _effectiveRange);

// Friis free-space path loss, normalised to the reference range so the
// signal fraction is 1.0 at the reference range.  The masks and the jammer
// add decibels.  All UNSOURCED.
private _freqHz = 3e8;                                   // UNSOURCED
private _terrainDb = 12;                                 // UNSOURCED
private _urbanDb = 6;                                    // UNSOURCED
private _jamDb = 30;                                     // UNSOURCED
private _refFSPL = (20 * log _refRange) + (20 * log _freqHz) - 147.55;
private _fspl = (20 * log (_dist max 1)) + (20 * log _freqHz) - 147.55;
private _maskDb = (_terrain * _terrainDb) + (_urban * _urbanDb) + (_jammer * _jamDb);
private _relativeDb = _refFSPL - _fspl - _maskDb;
private _signal = ((10 ^ (_relativeDb / 20)) max 0) min 1;

// A received link updates faster with more signal and more bandwidth.
private _baseInterval = 1.0;                             // UNSOURCED
private _refBandwidth = 100;                             // UNSOURCED
private _updateInterval = 0;
if (_received) then {
    _updateInterval = (_baseInterval * (_refBandwidth / _bw)) / (_signal max 0.1);
};

// Track age rises as the signal falls.  UNSOURCED.
private _trackAgeMax = 30;                               // UNSOURCED
private _trackAge = _trackAgeMax * (1 - _signal);

// Added position error rises as the signal falls, with a lost-link penalty.
private _errorMax = 25;                                  // UNSOURCED
private _errorLost = 15;                                 // UNSOURCED
private _addedError = _errorMax * (1 - _signal);
if (!_received) then {
    _addedError = _addedError + _errorLost;
};

private _state = "lost";
if (_received) then { _state = "received"; };

[_state, _updateInterval, _trackAge, _addedError]
