/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_cartography.
// The MGRS map and GPS settings moved here from aee_optics and took the
// aee_cartography_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module token
// changes. The terrainTables entry is the moved preInit global, carried here
// so the pair is recorded with the module that owns it.
[
    ["aee_optics_mgrsEnabled", "aee_cartography_mgrsEnabled"],
    ["aee_optics_mgrsPrecision", "aee_cartography_mgrsPrecision"],
    ["aee_optics_mgrsPrecisionAuto", "aee_cartography_mgrsPrecisionAuto"],
    ["aee_optics_mgrsMapGrid", "aee_cartography_mgrsMapGrid"],
    ["aee_optics_mgrsCursorReadout", "aee_cartography_mgrsCursorReadout"],
    ["aee_optics_terrainTables", "aee_cartography_terrainTables"]
]
