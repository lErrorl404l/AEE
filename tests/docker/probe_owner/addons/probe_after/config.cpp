/* SPDX-License-Identifier: GPL-2.0-or-later */
// Merge-order probe, AFTER variant (ADR-027). Declares requiredAddons
// {"aee_mobility"}, so the engine loads it after AEE and the probe wins the
// merge for the class both declare. This is the ceiling: a mod that names AEE
// and loads after it takes the class. The child restates its parent.
class CfgPatches {
    class probe_after {
        name = "AEE Merge-Order Probe (after)";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.0;
        requiredAddons[] = {"aee_mobility"};
        author = "AEE";
    };
};

class CfgVehicles {
    class B_MBT_01_base_F;
    class B_MBT_01_cannon_F: B_MBT_01_base_F {
        mass = 999999;
    };
};
