#include "..\script_component.hpp"

/*
Consistency log emitter.

The runtime monitor emits its lines through this one function, so the AEE_LOG
macros stay in a single place and the monitor's evaluation logic stays free of
engine macros.  The macro adds the [AEE][core][<level>] tag.

Arguments:
  0: String - the message, without the AEE tag.
  1: String - "INFO" for the first-run summary, "WARN" (default) otherwise.

Returns: Nothing.
*/

params [
    ["_line", "", [""]],
    ["_level", "WARN", [""]]
];

if (_level == "INFO") exitWith { AEE_LOG_INFO(_line); };

AEE_LOG_WARN(_line);
