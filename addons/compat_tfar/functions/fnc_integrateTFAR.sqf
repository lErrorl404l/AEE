#include "..\script_component.hpp"
/*
    AEE — TFAR Signal Integration

    Per-tick update of TFAR radio signal multipliers using AEE's radio
    propagation index.  Called from the compat-layer PFH every ~5 s.

    Propagation index (0.3–2.0) is mapped to a signal multiplier (0.3–1.5)
    and applied to both sending and receiving signal strength.

    Skips if TFAR is not loaded or AEE master switch is off.
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "task_force_radio")) exitWith {};
if (!(missionNamespace getVariable ["aee_core_enabled", false])) exitWith {};

private _propIdx = (missionNamespace getVariable ["aee_core_radioPropagationIndex", 0]);
if (_propIdx <= 0) then { _propIdx = 1.0 };

// propIdx 0.3 → mult 0.58, propIdx 1.0 → mult 1.0, propIdx 2.0 → mult 1.6
private _mult = ((_propIdx - 1) * 0.6) + 1;
_mult = _mult max 0.3 min 1.5;

// Sending — how far the player's transmissions reach
missionNamespace setVariable ["TFAR_sendingSignalMultiplier", _mult];
// Receiving — how clearly the player hears distant transmissions
missionNamespace setVariable ["TFAR_receivingSignalMultiplier", _mult];
