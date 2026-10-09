#include "script_component.hpp"

AEE_MODULE_POST_INIT

// hydrology has no postInit work of its own: it is a pure kernel set driven by
// the core environment tick.  The module still runs postInit so its
// aee_hydrology_postInit health flag is set, which the module-health contract
// requires of every non-compat module.
