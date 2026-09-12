#include "..\script_component.hpp"
/*
    AEE — TFAR Signal Integration

    Per-tick update of TFAR radio signal multipliers using AEE's radio
    propagation index.  Called from the compat-layer PFH every ~5 s.

    Propagation index (0.3–2.0) is mapped to a signal multiplier (0.3–1.5).

    TFAR API (verified against TFAR 1.x source):
      • Per-unit player variables, NOT missionNamespace:
        - tf_sendingDistanceMultiplicator (read at each PTT press)
        - tf_receivingDistanceMultiplicator (read every 0.3 s)
      • Global TFAR_globalRadioRangeCoef also scales range.
      • Setting both multipliers equal is a net no-op: the range check
        `distance × recvMult < tf_range × sendMult` cancels them.  AEE
        therefore scales sending only; receiving stays at 1.0 so a weak
        transmission is genuinely harder to hear at range.

    Skips if TFAR is not loaded or AEE master switch is off.
    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "task_force_radio")) exitWith {};
if (!(missionNamespace getVariable ["aee_core_enabled", false])) exitWith {};

private _propIdx = (missionNamespace getVariable ["aee_radio_radioPropagationIndex", 0]);
if (_propIdx <= 0) then { _propIdx = 1.0 };

// propIdx 0.3 → mult 0.58, propIdx 1.0 → mult 1.0, propIdx 2.0 → mult 1.6
private _mult = ((_propIdx - 1) * 0.6) + 1;
_mult = _mult max 0.3 min 1.5;

// Sending — how far the player's transmissions reach (per-unit variable)
player setVariable ["tf_sendingDistanceMultiplicator", _mult];
// Receiving — left at default 1.0 so the sending scale is not cancelled
