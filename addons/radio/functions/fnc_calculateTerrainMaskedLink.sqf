#include "..\script_component.hpp"

/*
Terrain-masked diffraction loss for one radio link.

Samples the terrain along the link and runs the Deygout diffraction kernel
(fnc_calculateTerrainDiffraction, ITU-R P.526-16 section 4.1/4.3) over the
profile.  The result is the excess loss the terrain adds on top of the
free-space path loss.

This is the per-link entry point: a caller with a real transmitter and
receiver (a radio pair, a command link) passes their positions and gets the
terrain masking for that geometry.  fnc_calculateRadioPropagation uses it
for the nominal observer link.

The wavelength follows the link frequency; the transmitter and receiver
antenna heights default to 2 m above their terrain, the handheld reference.

Arguments:
  0: Array  - transmitter position, ASL
  1: Array  - receiver position, ASL
  2: Number - link frequency, Hz (default 1e8)
  3: Number - transmitter antenna height above terrain, m (default 2)
  4: Number - receiver antenna height above terrain, m (default 2)
  5: Number - nominal profile sample spacing, m (default 50)

Returns the excess diffraction loss in dB (0 for a clear or degenerate link).
Public: No
*/

params [
    ["_txPos", [], [[]]],
    ["_rxPos", [], [[]]],
    ["_freqHz", 1e8, [0]],
    ["_txAGL", 2, [0]],
    ["_rxAGL", 2, [0]],
    ["_step", 50, [0]]
];

if ((count _txPos < 2) || (count _rxPos < 2)) exitWith { 0 };

private _dx = (_rxPos select 0) - (_txPos select 0);
private _dy = (_rxPos select 1) - (_txPos select 1);
private _dist = sqrt ((_dx * _dx) + (_dy * _dy));
if (_dist <= 0) exitWith { 0 };

private _profile = [_txPos, _rxPos, _step] call FUNC(sampleTerrainProfile);
if ((count _profile) < 2) exitWith { 0 };

// The sampler may widen the spacing to stay inside the cap, so derive the
// actual spacing from the returned profile rather than assuming _step.
private _actualStep = _dist / ((count _profile) - 1);
private _lambda = 3e8 / (_freqHz max 1);

[_profile, _actualStep, _txAGL, _rxAGL, _lambda] call FUNC(calculateTerrainDiffraction)
