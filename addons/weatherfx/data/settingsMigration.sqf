/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_weatherfx.
// The settings moved here from their source addon and took the
// aee_weatherfx_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_fx_exhaustShimmerAlpha", "aee_weatherfx_exhaustShimmerAlpha"],
    ["aee_fx_heatHazeEnabled", "aee_weatherfx_heatHazeEnabled"],
    ["aee_fx_heatHazeMaxAlpha", "aee_weatherfx_heatHazeMaxAlpha"],
    ["aee_fx_lightningBrightness", "aee_weatherfx_lightningBrightness"],
    ["aee_fx_lightningFXChance", "aee_weatherfx_lightningFXChance"],
    ["aee_fx_lightningIgnitionChance", "aee_weatherfx_lightningIgnitionChance"],
    ["aee_fx_rainDropDensity", "aee_weatherfx_rainDropDensity"],
    ["aee_fx_rainVehicleSoundVolume", "aee_weatherfx_rainVehicleSoundVolume"],
    ["aee_fx_severeWeatherBlur", "aee_weatherfx_severeWeatherBlur"],
    ["aee_fx_thunderVolume", "aee_weatherfx_thunderVolume"],
    ["aee_fx_windNoiseVolume", "aee_weatherfx_windNoiseVolume"]
]
