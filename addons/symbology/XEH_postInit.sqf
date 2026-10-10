#include "script_component.hpp"

AEE_MODULE_POST_INIT

// The dynamic variation selector (aee-dynamic-variation-system).  A CBA keybind
// in the AEE category opens the generated display; the open kernel no-ops
// safely when the map is closed.
["AEE", "VariationSelector", [LLSTRING(variationSelector), "Open the AEE symbol variation selector"], {
    [] call FUNC(variationDialogOpen);
}, {}] call CBA_fnc_addKeybind;

// NATO/OPFOR map symbols: applies the AEE symbols as real engine markers
// while the map is open, client-local and reversible.  NATO/OPFOR 3D world
// symbols: draws the real AEE marker texture in the 3D view.  The engine's
// own unit icons remain; these workers do not remove them.
if (hasInterface) then {
    [] call FUNC(symbologyMarkers);
    [] call FUNC(symbologyWorldDraw);
};
