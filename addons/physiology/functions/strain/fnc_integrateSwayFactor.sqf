#include "..\..\script_component.hpp"

/*
ACE3 weapon-sway integration for the shooter stability index.

Registers a MULTIPLIER sway factor with ACE3.  ACE3's sway loop
(fnc_swayLoop, every 0.5 s) combines all baseline factors by max, all
multiplier factors by product, then sets the aim coefficient:

    ACE_player setCustomAimCoef (baselineMax * multiplierProduct)

A multiplier < 1 lowers the aim coefficient, which increases sway.
AEE's stability index (0..1) maps directly: stability 1.0 -> multiplier
1.0 (no change); stability 0.3 -> multiplier 0.3 (sway multiplied ~3.3x).
ACE3's own stamina/rested/deployed factors are baselines (max-combined),
so AEE's multiplier scales them multiplicatively without conflicting.

The registration is one-shot at postInit.  The factor code reads the
stability index computed by fnc_calculateShooterStability (run on the
update tick), so it stays in sync with the environment PFH.

Input:  []
Output: true when registered, false when ACE3 is absent
*/

if (!isClass (configFile >> "CfgPatches" >> "ace_common")) exitWith { false };
if (!isClass (configFile >> "CfgPatches" >> "ace_advanced_fatigue")) exitWith { false };

["multiplier", {
    missionNamespace getVariable [QEGVAR(core,shooterStability), 1.0]
}, QUOTE(ADDON)] call ace_common_fnc_addSwayFactor;

true
