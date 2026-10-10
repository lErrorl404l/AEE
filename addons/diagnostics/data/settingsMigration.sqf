/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_diagnostics.
// The four switches moved here from aee_core and took the aee_diagnostics_*
// names. fnc_migrateLegacySettings copies each set old value to the new name.
[
    ["aee_core_consistencyCheck", "aee_diagnostics_consistencyCheck"],
    ["aee_core_consistencyInterval", "aee_diagnostics_consistencyInterval"],
    ["aee_core_consistencyStrict", "aee_diagnostics_consistencyStrict"],
    ["aee_core_diagnostic", "aee_diagnostics_diagnostic"]
]
