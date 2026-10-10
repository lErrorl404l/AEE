/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_vehicles.
// The settings moved here from aee_mobility and took the aee_vehicles_* names.
// fnc_migrateLegacySettings copies each set old value to the new name. The
// leaf is preserved verbatim, so only the module token changes.
[
    ["aee_mobility_estimateVehicleMassEnabled", "aee_vehicles_estimateVehicleMassEnabled"],
    ["aee_mobility_minEnginePower", "aee_vehicles_minEnginePower"],
    ["aee_mobility_vehicleCouplingEnabled", "aee_vehicles_vehicleCouplingEnabled"]
]
