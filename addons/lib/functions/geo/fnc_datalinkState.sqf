#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_datalinkState
 *
 * Link budget of a VHF/UHF tactical data radio between two ground units.
 * Pure.
 *
 *   Pr = Pt + Gt + Gr - (FSPL + Ldiff + Lexcess)
 *   FSPL  = 32.45 + 20 log10(f MHz) + 20 log10(d km)  (ITU-R P.525)
 *   Ldiff = Bullington diffraction over the terrain profile
 *           (ITU-R P.526-15 s.4.5.1, fnc_bullingtonLoss)
 *   Lexcess the environment loss the radio module publishes
 *           (aee_radio_excessLossDB: D-layer, flare, battery, EMP)
 * The report is received when Pr reaches the receiver sensitivity.  The
 * caller passes the radio: the defaults are the L3Harris AN/PRC-152A
 * data sheet (5 W = 37 dBm; -116 dBm at 12 dB SINAD, FM 30-152 MHz).
 * Vegetation loss (ITU-R P.833) needs the foliage depth along the path and
 * is not included.
 *
 * Arguments:
 *   0: txDbm   <NUMBER> transmit power, dBm
 *   1: gainDbi <NUMBER> transmit plus receive antenna gain, dBi
 *   2: sensDbm <NUMBER> receiver sensitivity, dBm
 *   3: fMHz    <NUMBER> frequency, MHz
 *   4: dKm     <NUMBER> path length, km
 *   5: dist    <ARRAY>  profile point distances, km
 *   6: hgt     <ARRAY>  profile point heights above sea level, m
 *   7: hts     <NUMBER> transmit antenna height above sea level, m
 *   8: hrs     <NUMBER> receive antenna height above sea level, m
 *   9: excessDb <NUMBER> environment excess loss, dB
 *
 * Return: [state, receivedDbm, marginDb, pathLossDb]; state "received" or
 *         "lost".
 */
params [
    ["_txDbm", 37, [0]], ["_gainDbi", 0, [0]], ["_sensDbm", -116, [0]], ["_fMHz", 100, [0]],
    ["_dKm", 1, [0]], ["_dist", [], [[]]], ["_hgt", [], [[]]],
    ["_hts", 2, [0]], ["_hrs", 2, [0]], ["_excessDb", 0, [0]]
];
private _d = _dKm max 0.001;
private _fspl = 32.45 + (20 * log _fMHz) + (20 * log _d);
private _diff = [_d, _dist, _hgt, _hts, _hrs, _fMHz] call FUNC(bullingtonLoss);
private _loss = _fspl + _diff + (_excessDb max 0);
private _pr = _txDbm + _gainDbi - _loss;
private _margin = _pr - _sensDbm;
[["lost", "received"] select (_margin >= 0), _pr, _margin, _loss]
