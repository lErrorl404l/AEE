/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_altitude.
// The settings moved here from aee_physiology and took the aee_altitude_*
// names.  fnc_migrateLegacySettings copies each set old value to the new
// name.  The leaf is preserved verbatim, so only the module token changes.
[
    ["aee_physiology_RapidAscentThreshold", "aee_altitude_RapidAscentThreshold"],
    ["aee_physiology_AMSOffsetAltitude", "aee_altitude_AMSOffsetAltitude"],
    ["aee_physiology_HypoxiaRecovery", "aee_altitude_HypoxiaRecovery"],
    ["aee_physiology_glocEnabled", "aee_altitude_glocEnabled"],
    ["aee_physiology_agsmAvailable", "aee_altitude_agsmAvailable"],
    ["aee_physiology_gsuitEquipped", "aee_altitude_gsuitEquipped"],
    ["aee_physiology_seatReclined", "aee_altitude_seatReclined"]
]
