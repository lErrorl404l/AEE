/* SPDX-License-Identifier: GPL-2.0-or-later */
// Direction probe host (ADR-027). A stand-in that declares the ACE CfgPatches
// surface the compat_ace3 addon keys on, so its two directions run live under
// Docker without the real ACE3 mod. It is NOT ACE3 and ships no ACE code. No
// sibling requiredAddons: a self-reference in one PBO is a circular
// dependency.
class CfgPatches {
    class ace_weather {
        name = "probe_host ace_weather stand-in";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.0;
        requiredAddons[] = {};
        author = "AEE";
    };
    class ace_medical {
        name = "probe_host ace_medical stand-in";
        units[] = {};
        weapons[] = {};
        requiredVersion = 1.0;
        requiredAddons[] = {};
        author = "AEE";
    };
};
