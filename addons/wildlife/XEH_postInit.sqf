#include "script_component.hpp"

AEE_MODULE_POST_INIT

// The client tick is client-local cosmetic ecology.  A machine with no
// player starts nothing, so a dedicated server stays inert.
if (hasInterface) then {
    [] call FUNC(initWildlife);
    // Stop the client tick and release its ambient source and emitters on
    // mission end, so a mission restart does not leave the PFH and the looping
    // sources behind.  The optics addon registers the same teardown for its
    // post-process handles.
    addMissionEventHandler ["Ended", {
        [] call FUNC(teardownWildlife);
    }];
};
