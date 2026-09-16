#include "..\script_component.hpp"
/*
Dump the performance counters to the RPT (issue #97).

Reads aee_perfCounters (populated by the BEGIN/END_COUNTER macros in
addons/main/script_debug.hpp, compile-time gated behind
ENABLE_PERFORMANCE_COUNTERS).  Skips the first 2 samples of each counter
(warm-up), averages the closed samples, and prints ms per call plus the
PFH registry (when the CBA_fnc_addPerFrameHandler override is active).

The counters only exist in dev builds (hemtt build -D
ENABLE_PERFORMANCE_COUNTERS); in production the macros expand to nothing
and aee_perfCounters is never created, so this function is a no-op.

Input:  none
Output: none
*/

// ─── PFH registry ────────────────────────────────────────────────────────
if (!isNil "aee_pfhCounter") then {
    diag_log text "=== AEE REGISTERED PFH HANDLERS ===";
    {
        _x params ["_pfh", "_parameters"];
        private _isActive = ["ACTIVE", "REMOVED"] select isNil {
            CBA_common_PFHhandles select (_pfh select 0)
        };
        diag_log text format [
            "PFH id=%1 [%2, delay %3] %4:%5",
            _pfh select 0,
            _isActive,
            _parameters select 1,
            _pfh select 1,
            _pfh select 2
        ];
    } forEach aee_pfhCounter;
    diag_log text "=== END PFH REGISTRY ===";
};

// ─── Counter results ─────────────────────────────────────────────────────
if (isNil "aee_perfCounters") exitWith {
    diag_log text "[AEE] No performance counters (build without ENABLE_PERFORMANCE_COUNTERS)";
};

diag_log text "=== AEE COUNTER RESULTS (ms/call, avg) ===";
private _report = [];
{
    private _counter = _x;
    private _total = 0;
    private _count = 0;

    // Skip the first 2 entries: [name, firstStart] then samples.  The
    // first sample after creation is part of the warm-up.
    for "_i" from 3 to (count _counter - 1) do {
        private _pair = _counter select _i;
        private _dt = (_pair select 1) - (_pair select 0);
        if (_dt >= 0) then {
            _total = _total + _dt;
            _count = _count + 1;
        };
    };

    if (_count > 0) then {
        private _avgMs = (_total / _count) * 1000;
        _report pushBack [_avgMs, _counter select 0];
    };
} forEach aee_perfCounters;

_report sort false;  // descending: heaviest first

{
    _x params ["_avgMs", "_name"];
    diag_log text format ["%1 ms/call  %2", [_avgMs, 3] call CBA_fnc_formatNumber, _name];
} forEach _report;

diag_log text format ["=== END COUNTER RESULTS (%1 counters, %2 samples) ===", count _report, count aee_perfCounters];

nil
