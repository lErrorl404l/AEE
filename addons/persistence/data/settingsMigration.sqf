/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_persistence.
// The settings moved here from aee_environmental and took the
// aee_persistence_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_environmental_DewRate", "aee_persistence_DewRate"],
    ["aee_environmental_FlashFloodThreshold", "aee_persistence_FlashFloodThreshold"],
    ["aee_environmental_FrostAccumRate", "aee_persistence_FrostAccumRate"],
    ["aee_environmental_FrostDecayRate", "aee_persistence_FrostDecayRate"],
    ["aee_environmental_WettingRate", "aee_persistence_WettingRate"],
    ["aee_environmental_groundFrostEnabled", "aee_persistence_groundFrostEnabled"],
    ["aee_environmental_slabDensity", "aee_persistence_slabDensity"],
    ["aee_environmental_slabDepth", "aee_persistence_slabDepth"]
]
