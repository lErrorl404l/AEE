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
// and the lint stays clean) but gated by the runtime flag.  Set it in the
// settings UI (AEE, Log Debug Output) or from the debug console:
//   aee_core_logDebug = true;
// Per-module:  aee_<component>_logDebug = true;  (AEE Diagnostics settings)
//
// The per-module flag is tested with the module's own name, so tracing
// one module does not drown the RPT in every other module's lines.
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
// The module trace switch, evaluated once so a caller that needs to skip
// expensive work (a surfaceType query, an engine call) can test it BEFORE
// building the message. AEE_LOG_DEBUG always builds its message, which is
// the wrong shape for a guard.
#define AEE_TRACE_ON (missionNamespace getVariable [QGVAR(logDebug), false] || missionNamespace getVariable ["aee_core_logDebug", false] || missionNamespace getVariable [format ["aee_%1_logDebug", QUOTE(COMPONENT)], false])
#define AEE_LOG_DEBUG(msg) if (AEE_TRACE_ON) then { diag_log text format ["[AEE][%1][DEBUG] %2", QUOTE(COMPONENT), msg]; };
#define AEE_LOG_TRACE(msg) if (AEE_TRACE_ON) then { diag_log text format ["[AEE][%1][TRACE] %2", QUOTE(COMPONENT), msg]; };

// ── Settings declaration ────────────────────────────────────────────────────
// CBA 3.19.0 has NO addSettingSimple and NO addMacroParentSettings, verified
// against CBA master e457d6e, so the 6-element array is ours to wrap.  AEE
// declares 188 settings across 19 files and the shape was hand-written every
// time; 166 of them now go through the three macros below.
//
// HEMTT'S PREPROCESSOR IS NOT BRACKET AWARE.  A macro argument is split on
// EVERY comma, including commas inside [], which the engine reported as
// error[PE9] "function call with incorrect number of arguments" when handed
// [0, 10, 5, 0.1] as one argument.  134 of the 188 settings are SLIDER with
// exactly that valueInfo shape, so a macro can never receive it.  Every
// argument below is therefore a SCALAR and the array is built in the BODY.
// The category and the slider bounds are passed as separate scalars, never as
// arrays.  warning[PW3] padding a macro argument also fires at the CALL SITE,
// so every invocation is emitted with no space after any comma.
//
// DOUBLES is var1##_##var2, so the second argument carries NO leading
// underscore: DOUBLES(h,_Name) pastes h__Name and matches no declared key,
// which silently broke all 332 keys until HEMTT caught it.  The key pair is
// checked in Python as well, see TestSettingMacroStringtableContract.
//
// AEE_SETTING_ADVANCED is deliberately ABSENT.  An escape hatch whose
// parameters are bracketed cannot be called through this preprocessor, so it
// would be dead code and a trap for exactly the settings that needed it.
// The 22 settings that need a LIST type, a non-standard title key, or a real
// _code block stay in the hand-written long form.  AEE_SETTING_SLIDER_LOCAL is
// absent for the same reason: aee_core_biomeOverride is a LIST and
// aee_core_diagnostic is the only non-global CHECKBOX, so no non-global slider
// exists and the variant would have zero call sites.
// The 7th SLIDER argument is CBA's _trailingDecimals, NOT a step.  CBA's
// SLIDER valueInfo order is [min, max, default, trailingDecimals, isPercentage]
// (fnc_init.sqf) and the GUI formats the shown value with
// [value, 1, trailingDecimals] call CBA_fnc_formatNumber, which calls toFixed.
// A fractional value here is floored by toFixed, the "." search then fails,
// and the leading-zero padding emits the literal strings "000" or "001" on the
// slider.  Pass the number of decimal places the setting needs: a small
// non-negative integer.  Something requiring six places wants 4, not 6.
#define AEE_SETTING_TITLE(h) [LLSTRING(DOUBLES(h,Name)), LLSTRING(DOUBLES(h,Description))]
#define AEE_SETTING_CHECKBOX(h,cat,subcat,def) [QGVAR(h), "CHECKBOX", AEE_SETTING_TITLE(h), [cat, subcat], def, true, {}] call CBA_fnc_addSetting
#define AEE_SETTING_SLIDER(h,cat,subcat,mn,mx,def,dec) [QGVAR(h), "SLIDER", AEE_SETTING_TITLE(h), [cat, subcat], [mn, mx, def, dec], true, {}] call CBA_fnc_addSetting
#define AEE_SETTING_CHECKBOX_LOCAL(h,cat,subcat,def) [QGVAR(h), "CHECKBOX", AEE_SETTING_TITLE(h), [cat, subcat], def, false, {}] call CBA_fnc_addSetting

// ── Module init guard: the one line every XEH init file starts with ─────────
// CBA provides NO re-entrancy guard for postInit (fnc_postInit.sqf:19 is an
// isNil on a marker it never sets) and CBA_fnc_addEventHandler STACKS
// (fnc_addEventHandler.sqf pushBack, no dedupe), so a repeat init triples the
// per-event work unless the mod refuses it.  That refusal is this macro, and it
// is the mod's job alone.
//
// WHY A MACRO AND NOT A HELPER FUNCTION: the guard must expand with the
// CALLING addon's COMPONENT, so each addon gets its own flag.  A function
// cannot see the caller's component; a macro in this shared header expands at
// the use site, so QGVAR and AEE_LOG_INFO inside it resolve against the addon
// that wrote the init file.
//
// ONE FLAG PER XEH EVENT, NOT ONE FLAG PER ADDON.  preInit and postInit are
// different events that can both fire in the same session.  A single shared
// flag makes whichever runs second believe the addon is already initialised.
// That is not hypothetical: with one shared flag, optics preInit set it and
// optics postInit then exited before registering the 0.1 s sensor PFH, both
// player event handlers and the hitPart handler.  The whole module went dead
// and the log called it a routine "skipping repeat init".  Two flags make that
// structurally impossible, and the headless run caught it.
//
// The flag name IS the event name, so the RPT says which event repeated.  That
// is what you need when hunting a multi-init fault on the client, where a
// shared name would leave you guessing.
//
// The skip is LOGGED, not silent: a repeat init is a real fault and the RPT
// must keep showing it rather than hiding it behind a clean return.
//
// tools/tests/test_audit_regressions.py::TestInitIsIdempotent FAILS THE BUILD
// if an init file that registers anything omits its guard, or if the guard
// names the wrong event for its file.  Adding a module without either is a gate
// failure, not a latent triple-registration bug.
#define AEE_MODULE_PRE_INIT \
    if (missionNamespace getVariable [QGVAR(preInit), false]) exitWith { \
        AEE_LOG_INFO("module already initialised: skipping repeat preInit") \
    }; \
    missionNamespace setVariable [QGVAR(preInit), true];

#define AEE_MODULE_POST_INIT \
    if (missionNamespace getVariable [QGVAR(postInit), false]) exitWith { \
        AEE_LOG_INFO("module already initialised: skipping repeat postInit") \
    }; \
    missionNamespace setVariable [QGVAR(postInit), true];

// ── Error helper — breaks on purpose in debug, logs in release ────────────
#ifdef DEBUG_MODE_FULL
    #define AEE_ERROR(msg) ERROR(msg)
#else
    #define AEE_ERROR(msg) AEE_LOG_ERROR(msg)
#endif

#endif
