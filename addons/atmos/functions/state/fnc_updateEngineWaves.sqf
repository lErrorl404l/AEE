#include "..\..\script_component.hpp"

/*
Engine wave rendering from AEE's sea state (issue #141).

`time setWaves value` changes the engine waves value smoothly over `time`
seconds.  AEE's maritime model already computes the significant wave
height; this bridge feeds it to the renderer.

Mapping: the engine `waves` value is a normalised 0..1 amplitude scale and
the engine publishes no metre mapping.  The bridge normalises the
significant wave height to the model's own ceiling of 15 m (the clamp in
fnc_calculateSeaState).  This is a rendering normalisation, not a physical
constant, and it keeps the engine scale monotonic and unsaturated while the
physics is valid.

REQUIREMENT: the mission weather must be on Manual Override (editor, Intel
> Manual Override).  The value changes without it, but the engine renders
no wave change.

Reads:  QEGVAR(maritime,waveHeight_m)
Sets:   engine waves (time setWaves)
*/
if (!hasInterface) exitWith {};

private _fullScaleMetres = 15;   // fnc_calculateSeaState caps H_s at 15 m

private _waveH = missionNamespace getVariable [QEGVAR(maritime,waveHeight_m), 0];
if !(_waveH isEqualType 0) then { _waveH = 0; };
_waveH = (_waveH max 0) min _fullScaleMetres;

private _waves = _waveH / _fullScaleMetres;
0 setWaves _waves;
