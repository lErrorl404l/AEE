// CBA script_xeh.hpp — P:drive replacement for HEMTT
// https://github.com/CBATeam/CBA_A3/blob/master/addons/xeh/script_xeh.hpp
// XEH (Extended Event Handlers) macros for ACE3/AEE compat.
// ====================================================================================

#ifndef CBA_SCRIPT_XEH_HPP
#define CBA_SCRIPT_XEH_HPP

// ====================================================================================
// XEH PREP — compile a function and register it for XEH

#define PREP(var1) \
    QGVAR(var1) = COMPILE_FILE2(functions\DOUBLES(fnc,var1).sqf); \
    if (isNil QGVAR(var1)) then { \
        diag_log text format ["[XEH] Failed to compile %1 for %2", #var1, QUOTE(ADDON)]; \
    }

// ====================================================================================
// XEH INIT BLOCK PATTERNS
// These wrap init code so it runs at the correct phase.

#define XEH_PREINIT \
    private _preInit = {

#define XEH_POSTINIT \
    private _postInit = {

#define XEH_PREINIT_RECOUP(intensity) \
    private _preInit = { \
        if !(isClass (configFile >> "CfgPatches" >> QUOTE(ADDON))) exitWith {}; \

#define XEH_POSTINIT_RECOUP(intensity) \
    private _postInit = { \
        if !(isClass (configFile >> "CfgPatches" >> QUOTE(ADDON))) exitWith {}; \

// ====================================================================================
// CLOSE INIT BLOCKS

#define XEH_PREINIT_CLOSE \
    }; \
    if (isNil "CBA_missionTime") then { \
        [nil, nil, _preInit] call CBA_fnc_waitAndExecute; \
    } else { \
        call _preInit; \
    };

#define XEH_POSTINIT_CLOSE \
    }; \
    if (isNil "CBA_missionTime") then { \
        (_postInit) call CBA_fnc_directCall; \
    };

// ====================================================================================
// SHORTHAND (for config-based inits)

#define PRE_INIT private _preInit = {XEH_PREINIT_CLOSE
#define POST_INIT private _postInit = {XEH_POSTINIT_CLOSE

// ====================================================================================
// XEH EVENT HANDLER STRINGS (used in config.cpp)

#define XEH_EVENTHANDLER(var1) class Extended_##var1##_EventHandlers
#define XEH_EVENTHANDLER_STR(var1) QUOTE(XEH_EVENTHANDLER(var1))

#define XEH_DISPLAY var1
#define XEH_DISPLAY_LOAD class Extended_DisplayLoad_EventHandlers { \
    class ADDON { \
        onLoad = QUOTE(_this call FUNC(var1)); \
    }; \
};

// ====================================================================================
// MISSION XEH

#define CBA_MISSION(var1) class CfgMission {

// ====================================================================================
// VERSION CHECK

#define XEH_VERSION_CHECK \
    if (isNil "CBA_funcs_init") exitWith { \
        diag_log text format ["[XEH] CBA not initialized — cannot init %1", QUOTE(ADDON)]; \
    };

// ====================================================================================
// SERVER / DEDICATED / HC CHECKS

#define XEH_IS_SERVER isServer
#define XEH_IS_DEDICATED isDedicated
#define XEH_HAS_INTERFACE hasInterface

// ====================================================================================
// OBSOLETE / BACKCOMPAT MACROS

#define PREP_MAIN(var1) PREP(var1)

// ====================================================================================
// CBA_fnc_addClassEvent HANDLER — for config-based class event registration
// This macro is used to register classes for XEH processing in config.cpp

#define ADD_CLASS_EVENT(var1) \
    class ADDON { \
        class XEH_##var1 { \
            init = QUOTE(_this call FUNC(var1)); \
        }; \
    };

#endif
