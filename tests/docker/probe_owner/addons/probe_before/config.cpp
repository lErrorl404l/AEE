/* SPDX-License-Identifier: GPL-2.0-or-later */
// Merge-order probe, BEFORE variant (ADR-027). Declares no requiredAddons, so
// the engine loads it before AEE. AEE then loads last and wins the merge for
// the class both declare. The child restates its parent: a bare reopen is the
// Empty-syntax trap and the engine discards the inherited values.
class CfgPatches {
    class probe_before {
        name = "AEE Merge-Order Probe (before)";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.0;
        requiredAddons[] = {};
        author = "AEE";
    };
};

class CfgVehicles {
    class B_MBT_01_base_F;
    class B_MBT_01_cannon_F: B_MBT_01_base_F {
        mass = 999999;
    };
};
