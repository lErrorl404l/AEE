// initSettings.inc.sqf - CBA Settings registration for aee_ai
//
// The reusable substrate owns exactly one user setting, its diagnostics
// switch.  Every ecology knob lives in aee_wildlife, so the substrate stays
// free of fauna policy.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","AI",false);

// The native engine-AI hearing layer.  Off by default: the capability is
// present but inert until an operator enables it, so it never changes a
// mission that did not ask for it.
AEE_SETTING_CHECKBOX(nativeHearing,"AEE AI","Hearing",false);
// Data-driven pathfinding (issue #81).  Off by default: the driver runs only
// when a caller asks for a route and the operator has opted in.
AEE_SETTING_CHECKBOX(pathfinding,"AEE AI","Pathfinding",false);
