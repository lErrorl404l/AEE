/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
            "A3_Armor_F",
            "A3_Soft_F",
            "cba_main",
            "cba_xeh"
        };
        author = AUTHOR;
        authors[] = AUTHORS;
        url = URL;
        VERSION_CONFIG;
    };
};

/*
Armour re-alignment (issue #126, STANAG 4569 hierarchy).

Research basis (docs/wiki/research/vehicle-armour-research.md):
  - CfgVehicles armor is a HEALTH POOL: the damageResistance formula is
      (HIT*HIT)/Armor * (0.27/tgtRadius)^2
    and is INDEPENDENT of the bisurf penetration gate.  Raising armor
    makes the pool deeper (more hits to destroy), NOT impenetrable.
  - STANAG 4569: L1 ~4-5mm, L2 ~8mm, L3 ~18mm, L4 ~28-32mm,
    L5 ~50-80mm, L6 ~100mm+ RHAe.  Real vehicles: MRAP up to L3, IFV
    L4/L5, MBT L6 (Leopard 2A4 ~600mm KE, 2A6 ~930mm, T-90 ~690mm).
  - ACE3 does NOT own the armour config surface (verified from source).

This addon holds NO static vehicle class list.  Rebasing a vanilla class
onto another base discards the fields the engine reads from its real base
(CargoLight, fireDustEffect, textureTrackWheel, memoryPointTrack*, the
Damage array), and the engine then raises "No entry" for each one when it
loads the vehicle.  Protection is resolved DYNAMICALLY instead:

  fnc_getVehicleArmour   - the researched STANAG 4569 table, keyed by the
                           classname's family signal (B_MRAP, B_APC_*, MBT)
  fnc_deriveProtection   - the mass-based derivation when the table has no
                           row for the class
  fnc_penetrationGate    - the bisurf gate; reads the vanilla armor pool
                           only when neither of the above resolves

A vehicle AEE has never seen therefore resolves from its own facts: its
classname signal, its mass and its vanilla armour pool.  No per-class
config entry, and no map or mod name is baked in.
*/

#include "CfgEventHandlers.hpp"
