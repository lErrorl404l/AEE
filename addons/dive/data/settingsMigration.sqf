/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_dive.
// The settings moved here from aee_physiology and took the aee_dive_* names.
// fnc_migrateLegacySettings copies each set old value to the new name.  The
// leaf is preserved verbatim, so only the module token changes.
[
    ["aee_physiology_diveEnabled", "aee_dive_diveEnabled"],
    ["aee_physiology_diveGradientFactor", "aee_dive_diveGradientFactor"]
]
