// CBA script_macros_common.hpp — P:drive replacement for HEMTT
// https://github.com/CBATeam/CBA_A3/blob/master/addons/main/script_macros_common.hpp
// Minimal subset required by ACE3/AEE patterns.
// ====================================================================================

#ifndef CBA_SCRIPT_MACROS_COMMON_HPP
#define CBA_SCRIPT_MACROS_COMMON_HPP

// ====================================================================================
// PBO-PATH HELPERS

#define DOUBLES(var1,var2) var1##_##var2
#define TRIPLES(var1,var2,var3) var1##_##var2##_##var3
#define QUOTE(var1) #var1
#define QQUOTE(var1) QUOTE(QUOTE(var1))

#define ADDON DOUBLES(PREFIX,COMPONENT)

#define GVAR(var1) DOUBLES(PREFIX,var1)
#define QGVAR(var1) QUOTE(GVAR(var1))

#define FUNC(var1) DOUBLES(DOUBLES(PREFIX,fnc),var1)
#define QFUNC(var1) QUOTE(FUNC(var1))

#define MPFUNC(var1) DOUBLES(DOUBLES(PREFIX,mp),var1)
#define QMPFUNC(var1) QUOTE(MPFUNC(var1))

#define EFUNC(var1,var2) TRIPLES(DOUBLES(PREFIX,var1),fnc,var2)
#define QEFUNC(var1,var2) QUOTE(EFUNC(var1,var2))

// ====================================================================================
// PATH CONSTRUCTION

#define PATHTOF(var1) \MAINPREFIX\PREFIX\SUBPREFIX\COMPONENT\var1
#define QPATHTOF(var1) QUOTE(PATHTOF(var1))

#define PATHTOF_SYS(var1,var2) \MAINPREFIX\PREFIX\SUBPREFIX\var1\var2
#define QPATHTOF_SYS(var1,var2) QUOTE(PATHTOF_SYS(var1,var2))

#define COMPILE_FILE(var1) PATHTOF(var1)
#define QCOMPILE_FILE(var1) QUOTE(COMPILE_FILE(var1))

// ====================================================================================
// FUNCTION COMPILATION

#define PREP(var1) \
    QFUNC(var1) = COMPILE_FILE(functions\DOUBLES(fnc,var1).sqf)

#define PREP_RECOMPILE(var1) \
    QFUNC(var1) = COMPILE_FILE(functions\DOUBLES(fnc,var1).sqf); \
    if (isServer || hasInterface) then { \
        private _fnc = missionNamespace getVariable [QFUNC(var1), {}]; \
        if (!isNil "_fnc" && {!isNil "CBA_compileFunction"}) then { \
            [QFUNC(var1), QPATHTOF(functions\DOUBLES(fnc,var1).sqf)] call CBA_fnc_compileFunction; \
        }; \
    }

// ====================================================================================
// MODULE / CONFIG HELPERS

#define ADDON_CONFIG DOUBLES(PREFIX,COMPONENT)
#define QADDON_CONFIG QUOTE(ADDON_CONFIG)

#define MODULE(var1) DOUBLES(PREFIX,var1)
#define QMODULE(var1) QUOTE(MODULE(var1))

#define SETTINGS(var1) DOUBLES(PREFIX,var1)
#define QSETTINGS(var1) QUOTE(SETTINGS(var1))

// ====================================================================================
// LOGGING

#define LOG_1(var1) diag_log text format ["[%1] %2", QUOTE(PREFIX), var1]
#define LOG_2(var1,var2) diag_log text format ["[%1] (%2) %3", QUOTE(PREFIX), var1, var2]

#define LOG(var1) LOG_2(COMPONENT,var1)
#define LOG_SYS(var1,var2) LOG_2(DOUBLES(PREFIX,var1),var2)

#ifdef DEBUG_MODE_FULL
    #define DEBUG(var1) LOG(var1)
    #define DEBUG_SYS(var1,var2) LOG_SYS(var1,var2)
    #define DEBUG_LOG(var1) LOG(var1)
#else
    #define DEBUG(var1) /* disabled */
    #define DEBUG_SYS(var1,var2) /* disabled */
    #define DEBUG_LOG(var1) /* disabled */
#endif

#define ERROR(var1) \
    diag_log text format ["[%1] [ERROR] (%2) %3", QUOTE(PREFIX), COMPONENT, var1]; \
    if (isMultiplayer) then { \
        [QUOTE(PREFIX), COMPONENT, var1] call CBA_fnc_error; \
    }

#define WARNING(var1) \
    diag_log text format ["[%1] [WARNING] (%2) %3", QUOTE(PREFIX), COMPONENT, var1]

#define INFO(var1) \
    diag_log text format ["[%1] [INFO] (%2) %3", QUOTE(PREFIX), COMPONENT, var1]

// ====================================================================================
// MUTEX

#define __LOCK(VAR) waitUntil {VAR}
#define __UNLOCK(VAR) VAR = true

// ====================================================================================
// STRING TABLE

#define STRING(var1) QUOTE(STR_##var1)
#define QSTRING(var1) QUOTE(STRING(var1))

// ====================================================================================
// EXTENDED EVENT HANDLERS (XEH) — see script_xeh.hpp for full XEH macros

#include "\x\cba\addons\xeh\script_xeh.hpp"

// ====================================================================================
// CBA FUNCTION COMPILATION BRIDGE

#define COMPILE_FILE2(var1) COMPILE_FILE(var1)

#endif
