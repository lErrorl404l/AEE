/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_strain.
// The settings moved here from aee_physiology and took the aee_strain_*
// names.  fnc_migrateLegacySettings copies each set old value to the new
// name.  The leaf is preserved verbatim, so only the module token changes.
[
    ["aee_physiology_SweatRateScale", "aee_strain_SweatRateScale"],
    ["aee_physiology_RehydrationRate", "aee_strain_RehydrationRate"],
    ["aee_physiology_HeatStrokeSensitivity", "aee_strain_HeatStrokeSensitivity"],
    ["aee_physiology_crossSensitivityEnabled", "aee_strain_crossSensitivityEnabled"],
    ["aee_physiology_crossSensitivityScale", "aee_strain_crossSensitivityScale"],
    ["aee_physiology_fatigueEnabled", "aee_strain_fatigueEnabled"],
    ["aee_physiology_circadianAmplitude", "aee_strain_circadianAmplitude"],
    ["aee_physiology_stabilityEnabled", "aee_strain_stabilityEnabled"],
    ["aee_physiology_coldWeatherEnabled", "aee_strain_coldWeatherEnabled"],
    ["aee_physiology_movementSpeed", "aee_strain_movementSpeed"]
]
