/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_lighting.
// The settings moved here from aee_environmental and took the
// aee_lighting_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_environmental_dynamicAurora", "aee_lighting_dynamicAurora"],
    ["aee_environmental_dynamicMeteors", "aee_lighting_dynamicMeteors"],
    ["aee_environmental_dynamicMilkyWay", "aee_lighting_dynamicMilkyWay"],
    ["aee_environmental_dynamicStars", "aee_lighting_dynamicStars"],
    ["aee_environmental_starBrightnessScale", "aee_lighting_starBrightnessScale"],
    ["aee_environmental_starLightPollutionEnabled", "aee_lighting_starLightPollutionEnabled"],
    ["aee_environmental_weatherOwnership", "aee_lighting_weatherOwnership"]
]
