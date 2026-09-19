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

// PREPS(var2,var1): compile functions\<var2>\fnc_<var1>.sqf - the
// subfolder variant of PREP for categorised function trees (issue #203).
// Subfolders are purely organisational (PBOs flatten the path), so the
// function name stays flat (aee_X_fnc_<var1>) and callers use FUNC as
// normal.  The define name matches FUNC/EFUNC for HEMTT L-S29.
#define PREPS(var2,var1) TRIPLES(ADDON,fnc,var1) = compile preprocessFileLineNumbers QPATHTOF(functions\var2\DOUBLES(fnc,var1).sqf)

// AEE-specific convenience macros

// Path construction helpers (complement CBA's QUOTE/QPATHTOF/QGVAR)
#define AAEE(var1) DOUBLES(aee,var1)
#define QAEE(var1) QUOTE(AAEE(var1))

#define ACEGVAR(var1,var2) TRIPLES(ace,var1,var2)
#define QACEGVAR(var1,var2) QUOTE(ACEGVAR(var1,var2))

// AEE PBO path helpers
#define AEE_PATH(var1) \z\aee\addons\##var1
#define AEE_FILE(var1) AEE_PATH(COMPONENT)\##var1

// ── Leveled logging (consistent across all addons) ────────────────────────
// Every log line carries [AEE][<addon>][<LEVEL>] so the RPT can be grepped
// per module:  grep "\[AEE\]\[optics\]" *.rpt
//
// Levels:
//   ERROR  - always logged (even release).  Failures that must not be silent.
//   WARN   - always logged.  Degraded behaviour that is not fatal.
//   INFO   - always logged.  Lifecycle events: mode changes, handle create/
//            destroy, config load.  One line per event, not per tick.
//   DEBUG  - logged only when aee_core_logDebug is true (runtime flag).
//   TRACE  - logged only when aee_core_logDebug is true.
//
// DEBUG/TRACE are compiled IN (so intermediate variables are always used
// and the lint stays clean) but gated by the runtime flag.  Set it via
// debug console:  aee_core_logDebug = true;
// Per-module:      aee_core_logDebug_optics = true;
//
// GUIDANCE (write new code with these):
//   - one log line per LIFECYCLE event, not per tick (INFO)
//   - include the handle/object/unit that failed (ERROR)
//   - per-tick physics values belong in DEBUG, not INFO — never spam
// COMPONENT is a bare identifier (optics, thermal, ...) — stringify it with
// QUOTE() so the log tag reads "[AEE][optics]" not "[AEE][any]" (the latter
// is what format prints when the identifier is evaluated as an undefined
// variable).
#define AEE_LOG_ERROR(msg) diag_log text format ["[AEE][%1][ERROR] %2", QUOTE(COMPONENT), msg]
#define AEE_LOG_WARN(msg) diag_log text format ["[AEE][%1][WARN] %2", QUOTE(COMPONENT), msg]
#define AEE_LOG_INFO(msg) diag_log text format ["[AEE][%1][INFO] %2", QUOTE(COMPONENT), msg]
#define AEE_LOG_DEBUG(msg) if (missionNamespace getVariable [QGVAR(logDebug), false] || missionNamespace getVariable ["aee_core_logDebug", false]) then { diag_log text format ["[AEE][%1][DEBUG] %2", QUOTE(COMPONENT), msg]; };
#define AEE_LOG_TRACE(msg) if (missionNamespace getVariable [QGVAR(logDebug), false] || missionNamespace getVariable ["aee_core_logDebug", false]) then { diag_log text format ["[AEE][%1][TRACE] %2", QUOTE(COMPONENT), msg]; };

// ── Error helper — breaks on purpose in debug, logs in release ────────────
#ifdef DEBUG_MODE_FULL
    #define AEE_ERROR(msg) ERROR(msg)
#else
    #define AEE_ERROR(msg) AEE_LOG_ERROR(msg)
#endif

#endif
