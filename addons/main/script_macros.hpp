#ifndef AEE_SCRIPT_MACROS_HPP
#define AEE_SCRIPT_MACROS_HPP

// Include CBA's canonical macros (replaced via include/ for HEMTT dev builds)
#include "\x\cba\addons\main\script_macros_common.hpp"

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
