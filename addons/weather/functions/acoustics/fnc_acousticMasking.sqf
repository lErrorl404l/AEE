#include "..\..\script_component.hpp"

/*
Acoustic masking gate (issue #109).

A source is audible over the ambient noise floor when its level at the
listener exceeds the floor by a detection threshold:

    audible  <=>  L_signal(r) > L_ambient + threshold

The signal falls with distance by spherical spreading, 20*log10(r) dB (6 dB
per doubling), and the weather/terrain absorption and refraction enter
through AEE's published sound-propagation index
aee_weather_currentSoundPropagation (0.3 to 2.0), computed by
fnc_updateSoundPropagation.  The index scales the EFFECTIVE range: an index
above 1 carries the sound further, below 1 shorter.  This reuses the one
propagation model; it does not add a second.

The threshold is the caller's.  The published margins: in the critical band
a tone is detected near 0 dB signal-to-noise (Fletcher 1940, DOI
10.1103/RevModPhys.12.47); a signal is clearly audible when its A-weighted
level exceeds the ambient noise by more than 15 dB (ISO 7731:2003, auditory
danger signals, s.5.2.2).

The floor is broadband (see fnc_ambientNoiseLevel), so this gate is
broadband; the per-band critical-ratio refinement is not modelled.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.

Arguments:
  0: Number - the source level at 1 m, dB
  1: Number - the source-listener distance, m
  2: Number - the ambient noise floor, dB(A)
  3: Number - the sound-propagation index, 0.3 to 2.0
  4: Number - the detection threshold, dB

Returns:
  Array - [audible (Bool), margin (Number, dB; positive means audible)]
*/

params [
    ["_sourceLevelDb", 0, [0]],
    ["_distanceM", 0, [0]],
    ["_ambientDb", 0, [0]],
    ["_propagationIndex", 1, [0]],
    ["_thresholdDb", 6, [0]]
];

private _index = ((_propagationIndex max 0.3) min 2.0);
private _effective = (_distanceM max 1) / _index;
private _spreadDb = 20 * (log (_effective max 1));
private _signalDb = _sourceLevelDb - _spreadDb;
private _marginDb = _signalDb - _ambientDb - _thresholdDb;

[(_marginDb > 0), _marginDb]
