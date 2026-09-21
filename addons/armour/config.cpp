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
  - The vanilla ladder (verified locally from the installed game):
    offroad/hatchback 20, truck 40, MRAP 60, IFV/APC 270-500 (wheeled),
    500-900 (tracked), MBT 800.
  - STANAG 4569: L1 ~4-5mm, L2 ~8mm, L3 ~18mm, L4 ~28-32mm,
    L5 ~50-80mm, L6 ~100mm+ RHAe.  Real vehicles: MRAP up to L3, IFV
    L4/L5, MBT L6 (Leopard 2A4 ~600mm KE, 2A6 ~930mm, T-90 ~690mm).
  - ACE3 does NOT own the armour config surface (verified from source):
    this override coexists freely.  Script-side HandleDamage (the
    penetration gate) must return _oldDamage/0 and never re-inflate
    _damage.

The override re-aligns the RELATIVE ladder to the STANAG hierarchy.
The pool values are design targets (not mm): what matters is the
ratio between classes - a rifle round does NOT deplete an IFV's pool
in a few hits, and an MBT survives rifle/HEI.  Per-class:
  offroad/hatchback: L1 skin (kept near vanilla)
  truck:             L2/L3 (unarmoured cab, cargo flatbed)
  MRAP:              L2/L3 (stops rifle ball, dies to AP/12.7)
  IFV/APC:           L4/L5 (stops 12.7, dies to 25mm/AP/ATGM)
  MBT:               L6 (only APFSDS/ATGM-class defeats)
*/
class CfgVehicles {
    // --- STANAG L1: light skin (kept near vanilla) -----------------------
    class Car_F;                   // base class
    class Offroad_01_base_F: Car_F {
        armor = 30;                // vanilla 20 -> L1 skin, a rifle will hurt it
    };
    class Hatchback_01_base_F: Car_F {
        armor = 30;
    };

    // --- STANAG L2/L3: truck ---------------------------------------------
    // Unarmoured cab with a cargo flatbed: rifle ball stops at close range,
    // AP and 12.7 defeat it.
    class Truck_F;
    class Truck_01_base_F: Truck_F {
        armor = 90;                // vanilla 40 -> L2/L3 mid
    };

    // --- STANAG L2/L3: MRAP ----------------------------------------------
    // The complaint target: vanilla MRAP (60) is shredded by any rifle.
    // A real MRAP (Cougar, RG-33) is L2/L3: stops rifle ball and 7.62 AP,
    // defeated by 12.7 and ATGM.  The pool lift makes it the reliable
    // protected transport it should be.
    class MRAP_01_base_F: Car_F {
        armor = 160;               // vanilla 60 -> L3-ish
    };
    class MRAP_02_base_F: Car_F {
        armor = 160;
    };
    class MRAP_03_base_F: Car_F {
        armor = 160;
    };

    // --- STANAG L4/L5: IFV/APC -------------------------------------------
    // The vanilla wheeled IFVs (270-320) and tracked APCs (500) sit below
    // their real protection.  An IFV (Bradley, Warrior, BMP) is L4/L5:
    // stops 12.7 all round, 25mm frontal, defeated by 30mm APFSDS/ATGM.
    class APC_Wheeled_01_base_F: Car_F {
        armor = 420;               // vanilla 320 -> L4
    };
    class APC_Wheeled_02_base_F: Car_F {
        armor = 420;
    };
    class APC_Wheeled_03_base_F: Car_F {
        armor = 500;               // vanilla 480 -> L5-ish
    };
    class APC_Tracked_01_base_F: Car_F {
        armor = 600;               // vanilla 500 -> L5
    };
    class APC_Tracked_02_base_F: Car_F {
        armor = 600;
    };
    class APC_Tracked_03_base_F: Car_F {
        armor = 700;               // vanilla 900 -> L5 top (kept strong)
    };

    // --- STANAG L6: MBT ---------------------------------------------------
    // Real MBT KE (Leopard 2A4 ~600mm, 2A6 ~930mm, T-90 ~690mm RHAe).
    // The pool must be high enough that only APFSDS-class rounds (or
    // repeated ATGM hits) defeat it.  Vanilla 800 kept as the floor -
    // the tank is already the L6 benchmark; the change is compressing
    // the IFV gap below so tanks read as the class above, not a
    // slightly-better APC.
    class MBT_01_base_F: Car_F {
        armor = 1100;              // vanilla 800 -> L6 (APFSDS-class)
    };
    class MBT_02_base_F: Car_F {
        armor = 1100;
    };
    class MBT_03_base_F: Car_F {
        armor = 1100;
    };
};

