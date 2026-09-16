/*
 * Performance counter macros (issue #97).
 *
 * Copy of the ACE3 pattern (ACE3 addons/main/script_debug.hpp): compile-
 * time gated, so a production build carries ZERO overhead.
 *
 * Enable for dev by uncommenting the define below (whole mod), or by
 * defining DEBUG_ENABLED_AEE_MAIN in a hemtt build profile.  Production
 * builds leave both commented: the macros expand to nothing.
 *
 * Usage:
 *   #include "script_debug.hpp"
 *   private _fnc = {
 *       BEGIN_COUNTER(myFeature);
 *       ... work ...
 *       END_COUNTER(myFeature);
 *   };
 *
 * Every function needs END_COUNTER on EVERY exit path - if a function
 * exits early, the counter is left open and the sample is discarded by
 * the dump (it averages only closed samples).
 *
 * The macro namespace is AEE's (aee_ballistics_*counter etc via GVAR).
 * Dump with: [] call aee_main_fnc_dumpPerformanceCounters
 */

//#define ENABLE_PERFORMANCE_COUNTERS

#ifdef DEBUG_ENABLED_AEE_MAIN
//#define ENABLE_PERFORMANCE_COUNTERS
#endif

#ifdef ENABLE_PERFORMANCE_COUNTERS

// PFH registry: wrap CBA_fnc_addPerFrameHandler to record handle + file + line.
#define CBA_fnc_addPerFrameHandler { \
    private _ret = call CBA_fnc_addPerFrameHandler; \
    if (isNil "aee_pfhCounter") then { aee_pfhCounter = []; }; \
    aee_pfhCounter pushBack [[_ret, __FILE__, __LINE__], _this]; \
    _ret \
}

#define CREATE_COUNTER(x) \
    if (isNil "aee_perfCounters") then { aee_perfCounters = []; }; \
    GVAR(DOUBLES(x,counter)) = []; \
    GVAR(DOUBLES(x,counter)) set [0, QUOTE(GVAR(DOUBLES(x,counter)))]; \
    GVAR(DOUBLES(x,counter)) set [1, diag_tickTime]; \
    aee_perfCounters pushBack GVAR(DOUBLES(x,counter))

#define BEGIN_COUNTER(x) \
    if (isNil QUOTE(GVAR(DOUBLES(x,counter)))) then { CREATE_COUNTER(x) }; \
    GVAR(DOUBLES(x,counter)) set [2, diag_tickTime]

#define END_COUNTER(x) \
    GVAR(DOUBLES(x,counter)) pushBack [(GVAR(DOUBLES(x,counter)) select 2), diag_tickTime]

#define DUMP_COUNTERS ([__FILE__, __LINE__] call AEE_DUMPCOUNTERS_FNC)

#else

#define CREATE_COUNTER(x) ; /* disabled */
#define BEGIN_COUNTER(x) ; /* disabled */
#define END_COUNTER(x) ; /* disabled */
#define DUMP_COUNTERS ; /* disabled */

#endif
