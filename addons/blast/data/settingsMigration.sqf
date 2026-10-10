/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_blast.
// The settings moved here from their source addon and took the
// aee_blast_* names. fnc_migrateLegacySettings copies each set old value
// to the new name. The leaf is preserved verbatim, so only the module
// token changes.
[
    ["aee_fx_blastInjuryEnabled", "aee_blast_blastInjuryEnabled"]
]
