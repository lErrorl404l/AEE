#include "script_component.hpp"

AEE_MODULE_POST_INIT

// The client tick and the stimulus broadcast start here.  The whole layer is
// client-local cosmetic ecology, so a machine with no player runs nothing.
if (hasInterface) then {
    [] call FUNC(initAI);
};
