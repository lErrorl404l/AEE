#include "script_component.hpp"

AEE_MODULE_POST_INIT

// clothing has no postInit work of its own: it is a pure equipment-data
// lookup set driven by the physiology and thermal models.  The module still
// runs postInit so its aee_clothing_postInit health flag is set, which the
// module-health contract requires of every non-compat module.
