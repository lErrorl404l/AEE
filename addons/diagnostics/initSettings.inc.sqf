// initSettings.inc.sqf - CBA Settings registration for aee_diagnostics
//
// diagnostics owns the state dump, the performance counters and the
// cross-module consistency monitor. The consistency and diagnostic switches
// migrated here from aee_core (ADR-032); the defaults are unchanged.

// ── Diagnostics: trace switch ─────────────────────────────────────────────
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Diagnostics",false);

// ── Consistency monitor (AEE Debug > Diagnostics) ─────────────────────────
// The cross-module consistency monitor reads the published producer variables
// every consistencyInterval seconds and warns when a module disagrees.  The
// check is read-only and deterministic, so it runs on every machine.  Strict
// mode also warns on a row that passes but whose producers are not equal.
AEE_SETTING_CHECKBOX(consistencyCheck,"AEE Debug","Diagnostics",true);
AEE_SETTING_SLIDER(consistencyInterval,"AEE Debug","Diagnostics",1,60,10,0);
AEE_SETTING_CHECKBOX(consistencyStrict,"AEE Debug","Diagnostics",false);

// ── Diagnostic logging ────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX_LOCAL(diagnostic,"AEE Debug","Diagnostics",false);
