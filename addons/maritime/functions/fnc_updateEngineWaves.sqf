#include "..\script_component.hpp"

/*
Engine wave rendering from AEE's sea state (issue #141).

`time setWaves value` changes the engine waves value smoothly over `time`
seconds.  AEE's maritime model already computes the significant wave
height; this bridge feeds it to the renderer.

Mapping: the engine `waves` value is a normalised 0..1 amplitude scale (the
local engine reference calls it "0-1 wave intensity"; the engine publishes
no metre mapping).  The world declares the metre scale of that normalised
value in CfgWorlds >> <world> >> Sea >> MaxWave (map_altis config.cpp:486,
MaxWave = 0.25), so that field is the scale this bridge divides by.
The previous hard-coded 15 m was NOT an engine figure: it is AEE's own
Pierson-Moskowitz clamp ceiling in fnc_calculateSeaState.sqf:48, which would
have sent the engine a sea state about 60x the height Altis can represent.

REQUIREMENT: the mission weather must be on Manual Override (editor, Intel
> Manual Override).  The value changes without it, but the engine renders
no wave change.

Reads:  QGVAR(waveHeight_m)
Sets:   engine waves (time setWaves)
*/
if (!hasInterface) exitWith {};

// The world's own wave scale, in metres.  Fallback 0.25 is the Altis value
// (map_altis config.cpp:486); it is UNVERIFIED for other worlds, so read the
// world field first and fall back only when the field is absent or zero.
private _worldMaxWave = getNumber (configFile >> "CfgWorlds" >> worldName >> "Sea" >> "MaxWave");
if (_worldMaxWave <= 0) then { _worldMaxWave = 0.25; };
private _fullScaleMetres = _worldMaxWave;

private _waveH = missionNamespace getVariable [QGVAR(waveHeight_m), 0];
if !(_waveH isEqualType 0) then { _waveH = 0; };
_waveH = (_waveH max 0) min _fullScaleMetres;

private _waves = _waveH / _fullScaleMetres;
0 setWaves _waves;

// The command DB records that this write draws nothing unless the mission
// selects *Manual Override* in the Eden intel section (commands/setWaves.yml,
// acemod/arma3-wiki v2.22).  No command reads or sets that flag and the
// `waves` readback moves either way, so a script cannot detect or enable it.
// Warn once per session instead of a silent no-op.
[] call EFUNC(core,warnManualOverride);
