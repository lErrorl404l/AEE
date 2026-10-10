/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_thermal_display.
// The display settings moved here from aee_thermal and took the
// aee_thermal_display_* names. fnc_migrateLegacySettings copies each set old
// value to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_thermal_fusionAlwaysOn", "aee_thermal_display_fusionAlwaysOn"],
    ["aee_thermal_fusionFovFrame", "aee_thermal_display_fusionFovFrame"],
    ["aee_thermal_fusionHud", "aee_thermal_display_fusionHud"],
    ["aee_thermal_fusionOutline", "aee_thermal_display_fusionOutline"],
    ["aee_thermal_fusionSolidFill", "aee_thermal_display_fusionSolidFill"],
    ["aee_thermal_repaintHz", "aee_thermal_display_repaintHz"],
    ["aee_thermal_thermalAgcHunt", "aee_thermal_display_thermalAgcHunt"],
    ["aee_thermal_thermalAgcHuntPeriod", "aee_thermal_display_thermalAgcHuntPeriod"],
    ["aee_thermal_thermalFPN", "aee_thermal_display_thermalFPN"],
    ["aee_thermal_thermalHotBloom", "aee_thermal_display_thermalHotBloom"],
    ["aee_thermal_thermalImperfectionsEnabled", "aee_thermal_display_thermalImperfectionsEnabled"],
    ["aee_thermal_thermalNucDrift", "aee_thermal_display_thermalNucDrift"],
    ["aee_thermal_thermalPPEffects", "aee_thermal_display_thermalPPEffects"],
    ["aee_thermal_thermalPixelation", "aee_thermal_display_thermalPixelation"],
    ["aee_thermal_thermalWetDistortion", "aee_thermal_display_thermalWetDistortion"]
]
