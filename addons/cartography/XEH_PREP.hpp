// XEH_PREP.hpp - function prep includes for aee_cartography
//
// The map surface: MGRS grid and precision, the map overlay draw, the cursor
// and marker text, the font choice and the GPS readout.  Every kernel is
// PREP'd from functions/hud/ (the category the optics split carried over);
// callers use FUNC.

PREPS(hud,mapIconWorldSize);
PREPS(hud,mapLegendDraw);
PREPS(hud,mgrsGridLines);
PREPS(hud,mgrsMapDraw);
PREPS(hud,mgrsMapPrecision);
PREPS(hud,mgrsEffectivePrecision);
PREPS(hud,mgrsCursorText);
PREPS(hud,mgrsMarkerText);
PREPS(hud,mgrsFontFamily);
PREPS(hud,fontFamilyUsable);
PREPS(hud,formatGridDisplay);
PREPS(hud,hudFormatGrid);
PREPS(hud,gpsBuild);
PREPS(hud,gpsUpdate);
