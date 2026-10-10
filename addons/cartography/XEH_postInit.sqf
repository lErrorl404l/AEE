#include "script_component.hpp"

AEE_MODULE_POST_INIT

if (hasInterface) then {
    // MGRS map overlay: attaches a Draw handler to the engine map control
    // when the map opens.  Read-only, no marker is created or edited.
    [] call FUNC(mgrsMapDraw);
    // Physics-state tactical overlay (#155): the click-to-query tool.  It
    // installs the stackable MapSingleClick handler; the drawing layers are
    // drawn from the ONE Draw handler above, not a second rendering path.
    [] call FUNC(mapClickQuery);
    // MGRS GPS device readout: raised only while the player carries an
    // ItemGPS and the aee_cartography_mgrsEnabled setting is on.
    [FUNC(gpsUpdate), 0.1] call CBA_fnc_addPerFrameHandler;
};
