/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_hud.
// The ECOTI HUD and tracker settings moved here from aee_optics and took the
// aee_hud_* names. fnc_migrateLegacySettings copies each set old value to the
// new name. The leaf is preserved verbatim, so only the module token changes.
[
    ["aee_optics_hudEnabled", "aee_hud_hudEnabled"],
    ["aee_optics_trackerEnabled", "aee_hud_trackerEnabled"],
    ["aee_optics_trackerSuppressIcons", "aee_hud_trackerSuppressIcons"],
    ["aee_optics_trackerInterval", "aee_hud_trackerInterval"]
]
