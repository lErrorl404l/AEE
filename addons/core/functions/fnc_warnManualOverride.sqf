#include "..\script_component.hpp"

/*
Manual Override dependency warning, once per session.

`setWaves` and `setLightnings` change their value without the Eden intel
*Manual Override* flag, but the engine renders nothing (command DB
`setWaves` and `setLightnings`, acemod/arma3-wiki v2.22).  The command DB has
NO command that reads or sets that mission flag, and the readback (`waves`,
`lightnings`) moves either way, so a script can neither detect nor enable the
flag and cannot tell a render from a silent no-op.

The wave and lightning bridges call this once per session, so the operator
learns the dependency instead of seeing a silent no-op.  The flag lives on the
mission namespace, so the warning fires once for the whole bridge set.

Public: No
*/

if (missionNamespace getVariable [QGVAR(manualOverrideWarned), false]) exitWith {};
missionNamespace setVariable [QGVAR(manualOverrideWarned), true];

AEE_LOG_WARN("engine waves and lightnings render only with Manual Override set in Eden intel; without the flag the value changes and nothing is drawn");
