/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_flight.
// The settings moved here from aee_mobility and took the aee_flight_* names.
// fnc_migrateLegacySettings copies each set old value to the new name. The
// leaf is preserved verbatim, so only the module token changes.
[
    ["aee_mobility_airframeRadius", "aee_flight_airframeRadius"],
    ["aee_mobility_flightAeroPenalty", "aee_flight_flightAeroPenalty"],
    ["aee_mobility_flightTurbulence", "aee_flight_flightTurbulence"],
    ["aee_mobility_turbulenceRadius", "aee_flight_turbulenceRadius"],
    ["aee_mobility_turbulenceScale", "aee_flight_turbulenceScale"]
]
