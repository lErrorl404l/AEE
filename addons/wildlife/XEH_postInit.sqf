#include "script_component.hpp"

AEE_MODULE_POST_INIT

// The client tick is client-local cosmetic ecology.  A machine with no
// player starts nothing, so a dedicated server stays inert.
if (hasInterface) then {
    [] call FUNC(initWildlife);
};
