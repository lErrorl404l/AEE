/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_weather.
// The settings moved here from aee_environmental and took the
// aee_weather_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_environmental_BlowingSnowWindThreshold", "aee_weather_BlowingSnowWindThreshold"],
    ["aee_environmental_DustDevilTempThreshold", "aee_weather_DustDevilTempThreshold"],
    ["aee_environmental_FlareChance", "aee_weather_FlareChance"],
    ["aee_environmental_FlareDecayRate", "aee_weather_FlareDecayRate"],
    ["aee_environmental_FlareDuration", "aee_weather_FlareDuration"],
    ["aee_environmental_InversionBoost", "aee_weather_InversionBoost"],
    ["aee_environmental_MaxSnowDepth", "aee_weather_MaxSnowDepth"],
    ["aee_environmental_SandstormWindThreshold", "aee_weather_SandstormWindThreshold"],
    ["aee_environmental_SnowAccretionRate", "aee_weather_SnowAccretionRate"],
    ["aee_environmental_SoundPropagationScale", "aee_weather_SoundPropagationScale"],
    ["aee_environmental_logDebug", "aee_weather_logDebug"]
    ,["aee_physiology_ScentIntensity", "aee_weather_ScentIntensity"]
]
