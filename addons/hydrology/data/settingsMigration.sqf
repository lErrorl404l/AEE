/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_hydrology.
// The settings moved here from aee_mobility and took the aee_hydrology_*
// names. fnc_migrateLegacySettings copies each set old value to the new name.
// The leaf is preserved verbatim, so only the module token changes.
[
    ["aee_mobility_baseflowRate_perDay", "aee_hydrology_baseflowRate_perDay"],
    ["aee_mobility_bedSlope", "aee_hydrology_bedSlope"],
    ["aee_mobility_catchmentArea_m2", "aee_hydrology_catchmentArea_m2"],
    ["aee_mobility_manningN", "aee_hydrology_manningN"],
    ["aee_mobility_riverResponseRate", "aee_hydrology_riverResponseRate"],
    ["aee_mobility_riverSectionWidth_m", "aee_hydrology_riverSectionWidth_m"],
    ["aee_mobility_tidalReach_m", "aee_hydrology_tidalReach_m"]
]
