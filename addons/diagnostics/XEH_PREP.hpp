// XEH_PREP.hpp - function prep includes for aee_diagnostics
//
// The state dump, the performance counters and the cross-module consistency
// monitor. Registered via CBA's PREP system; each entry compiles
// functions/fnc_<name>.sqf at mission start.

PREP(consistencyFailureLine);
PREP(consistencyLoadTable);
PREP(consistencyLog);
PREP(diagnostic);
PREP(dumpPerformanceCounters);
PREP(dumpState);
PREP(evaluateConsistency);
PREP(reportModuleHealth);
PREP(runConsistencyCheck);
