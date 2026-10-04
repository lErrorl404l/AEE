#include "..\script_component.hpp"

/*
Bright-source blinding envelope.

The parent's blowout envelope (attack, hold, release) sets the recovery
TIMING.  This kernel maps the current blowout to the render scales: un-gated
Gen 1/2 tubes white out, gated Gen 3/PVS-31 tubes black out, and both lose
contrast.  MIL-I-49428 section 3.6.22 is phosphor persistence, NOT gate
recovery, and is not the source.

Arguments:
  0: Number - blowout state in [0, 1]
  1: Number - tier index (0 GEN1 .. 3 PVS31)
  2: Number - strength in [0, 1]

Returns:
  Array - [brightnessScale in [0, 2], contrastScale in [0, 1]].
*/

params [
    ["_blowout", 0, [0]],
    ["_tierIdx", 0, [0]],
    ["_strength", 1, [0]]
];

private _blind = _blowout * _strength;
_blind = (_blind max 0) min 1;

// _whiteMax, _blackMin and _contrastLoss are UNSOURCED modelling choices,
// bounded by the auto-gate literature.  They carry no numeric source.
private _whiteMax = [1.6, 1.4, 1.0, 1.0] select ((_tierIdx max 0) min 3);
private _blackMin = [1.0, 1.0, 0.15, 0.10] select ((_tierIdx max 0) min 3);
private _contrastLoss = 0.6;

private _brightnessScale = 1;
if (_tierIdx <= 1) then {
    // Un-gated tubes white out: brightness climbs toward _whiteMax.
    _brightnessScale = 1 + (_whiteMax - 1) * _blind;
} else {
    // Gated tubes black out: brightness collapses toward _blackMin.
    _brightnessScale = 1 - (1 - _blackMin) * _blind;
    _contrastLoss = 0.4;
};

private _contrastScale = 1 - _contrastLoss * _blind;

[(0 max _brightnessScale) min 2, (0 max _contrastScale) min 1]
