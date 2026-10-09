/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_particles.
// The settings moved here from their source addon and took the
// aee_particles_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_fx_atmosphericDustIntensity", "aee_particles_atmosphericDustIntensity"],
    ["aee_fx_logDebug", "aee_particles_logDebug"],
    ["aee_fx_vehicleDustDensity", "aee_particles_vehicleDustDensity"],
    ["aee_fx_vehicleDustIntensity", "aee_particles_vehicleDustIntensity"],
    ["aee_fx_weatherAlphaEnabled", "aee_particles_weatherAlphaEnabled"]
]
