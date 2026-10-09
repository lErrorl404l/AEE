/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_ambience.
// The settings moved here from their source addon and took the
// aee_ambience_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_wildlife_ambientEnabled", "aee_ambience_ambientEnabled"],
    ["aee_wildlife_callBudget", "aee_ambience_callBudget"],
    ["aee_wildlife_callRange", "aee_ambience_callRange"],
    ["aee_wildlife_communicationEnabled", "aee_ambience_communicationEnabled"],
    ["aee_wildlife_silenceDecay", "aee_ambience_silenceDecay"]
]
