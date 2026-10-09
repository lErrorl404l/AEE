/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_ltm.
// The settings moved here from their source addon and took the
// aee_ltm_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_nightvision_ltmDaylightFade", "aee_ltm_ltmDaylightFade"],
    ["aee_nightvision_ltmEnabled", "aee_ltm_ltmEnabled"]
]
