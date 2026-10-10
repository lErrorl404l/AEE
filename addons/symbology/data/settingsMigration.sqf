/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_symbology.
// The NATO/OPFOR symbology settings moved here from aee_optics and took the
// aee_symbology_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module token
// changes. The symbologyTables entry is the moved preInit global, carried
// here so the pair is recorded with the module that owns it.
[
    ["aee_optics_symbologyEnabled", "aee_symbology_symbologyEnabled"],
    ["aee_optics_symbologyFont", "aee_symbology_symbologyFont"],
    ["aee_optics_symbologyMarkers", "aee_symbology_symbologyMarkers"],
    ["aee_optics_symbologyPalette", "aee_symbology_symbologyPalette"],
    ["aee_optics_symbologySuppress", "aee_symbology_symbologySuppress"],
    ["aee_optics_symbologyUnits", "aee_symbology_symbologyUnits"],
    ["aee_optics_symbologyTables", "aee_symbology_symbologyTables"]
]
