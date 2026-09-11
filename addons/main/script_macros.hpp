/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AEE_SCRIPT_MACROS_HPP
#define AEE_SCRIPT_MACROS_HPP

// Stock CBA macros (vendored in include/x/cba for HEMTT preprocessing).
#include "\x\cba\addons\main\script_macros_common.hpp"

// ── Function compilation ────────────────────────────────────────────────────
// Stock CBA's PREP compiles from the addon root (fnc_<name>.sqf). AEE keeps
// the ACE3 convention of a functions/ subfolder, so PREP is overridden to
// compile functions\fnc_<name>.sqf. The defined name (TRIPLES(ADDON,fnc,x))
// matches FUNC/EFUNC, which HEMTT's L-S29 lint recognises as an assignment.
#undef PREP
#define PREP(var1) TRIPLES(ADDON,fnc,var1) = compile preprocessFileLineNumbers QPATHTOF(functions\DOUBLES(fnc,var1).sqf)

// AEE-specific convenience macros

// Path construction helpers (complement CBA's QUOTE/QPATHTOF/QGVAR)
#define AAEE(var1) DOUBLES(aee,var1)
#define QAEE(var1) QUOTE(AAEE(var1))

#define ACEGVAR(var1,var2) TRIPLES(ace,var1,var2)
#define QACEGVAR(var1,var2) QUOTE(ACEGVAR(var1,var2))

// AEE PBO path helpers
#define AEE_PATH(var1) \z\aee\addons\##var1
#define AEE_FILE(var1) AEE_PATH(COMPONENT)\##var1

// Logging helpers (mirror ACE3 pattern)
#define AEE_LOG(msg) diag_log text format ["[AEE] (COMPONENT) %1", msg]

// Error helper — breaks on purpose in debug, logs in release
#ifdef DEBUG_MODE_FULL
    #define AEE_ERROR(msg) ERROR(msg)
#else
    #define AEE_ERROR(msg) diag_log text format ["[AEE] [ERROR] (COMPONENT) %1", msg]
#endif

#endif
