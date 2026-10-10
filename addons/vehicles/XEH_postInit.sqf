#include "script_component.hpp"

AEE_MODULE_POST_INIT

// vehicles has no postInit work of its own: it is a pure kernel set driven by
// the core environment tick and the mobility coupling loops.  The module still
// runs postInit so its aee_vehicles_postInit health flag is set, which the
// module-health contract requires of every non-compat module.
