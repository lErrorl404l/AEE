// XEH_PREP.hpp - function prep includes for aee_hud
//
// The ECOTI environment HUD panels, the rangefinder and map-marker workers,
// and the signal-dependent tracker.  Every kernel is PREP'd from
// functions/hud/ (the category the optics split carried over); callers use
// FUNC.

PREPS(hud,hudBuild);
PREPS(hud,hudUpdate);
PREPS(hud,hudFormatHeading);
PREPS(hud,hudFormatRange);
PREPS(hud,hudRangefinder);
PREPS(hud,hudMarkers);
PREPS(hud,trackerDraw);
PREPS(hud,trackerProject);
PREPS(hud,trackerUpdate);
