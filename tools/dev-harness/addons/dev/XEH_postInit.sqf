// The dev channel starts only when the four-layer gate holds. Failure is a
// silent no-op: no per-frame handler, no verb table, no log line.
if !(call aee_dev_fnc_devGateLive) exitWith {};

aee_dev_verbs = call aee_dev_fnc_devVerbs;
