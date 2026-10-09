PREPS(fx,applyAtmosphericSeeingFX);
PREPS(fx,applyDewOnOpticsFX);
PREPS(fx,applyHeatShimmerFX);
PREPS(fx,applyMirageFX);
PREPS(fx,applyRainOnOpticsFX);
PREPS(fx,applySnowBlindnessFX);
PREPS(fx,applySolarGlareFX);
PREPS(sensor,calculateAtmosphericSeeing);
PREPS(sensor,calculateAttenuation);
PREPS(sensor,calculateDewOnOptics);
PREPS(sensor,calculateMirageIntensity);
PREPS(sensor,calculatePrecipitationVisibility);
PREPS(sensor,calculateRainOnOptics);
PREPS(sensor,calculateSmokePersistence);
PREPS(sensor,calculateSnowBlindness);
PREPS(sensor,calculateSolarGlare);
PREPS(sensor,calculateVehicleHeatShimmer);
PREPS(sensor,getOpticProperties);

PREPS(hud,formatGridDisplay);
PREPS(hud,gpsBuild);
PREPS(hud,gpsUpdate);
PREPS(hud,hudBuild);
PREPS(hud,hudFormatGrid);
PREPS(hud,hudFormatHeading);
PREPS(hud,hudFormatRange);
PREPS(hud,hudMarkers);
PREPS(hud,hudRangefinder);
PREPS(hud,hudUpdate);
PREP(dumpState);
PREPS(hud,fontFamilyUsable);
PREPS(hud,mgrsCursorText);
PREPS(hud,mgrsEffectivePrecision);
PREPS(hud,mgrsFontFamily);
PREPS(hud,mgrsGridLines);
PREPS(hud,mgrsMapDraw);
PREPS(hud,mgrsMapPrecision);
PREPS(hud,mgrsMarkerText);
PREPS(hud,trackerDraw);
PREPS(hud,trackerProject);
PREPS(hud,trackerUpdate);

// NATO/OPFOR map symbology: the pure symbol kernels and the engine adapters.
PREPS(symbology,symbolPalette);
PREPS(symbology,symbolFrame);
PREPS(symbology,symbolIcon);
PREPS(symbology,symbolResolve);
PREPS(symbology,symbologyMarkerType);
PREPS(symbology,symbologyMarkerColor);
PREPS(symbology,symbolCategory);
PREPS(symbology,symbologyMarkerCategory);
PREPS(symbology,symbologyUnitCategory);
PREPS(symbology,symbologyUnitDimension);
PREPS(symbology,symbologyUnitEchelon);
PREPS(symbology,symbologyAffiliation);
PREPS(symbology,symbologyPaletteFriendly);
PREPS(symbology,symbologyDimension);
PREPS(symbology,symbologyEchelon);
PREPS(symbology,symbologyEchelonMarker);
PREPS(symbology,symbologyEchelonSize);
PREPS(symbology,symbologyMarkers);
PREPS(symbology,symbologyMarkersApply);
PREPS(symbology,symbologyMarkersRestore);
PREPS(symbology,symbologyWorldDraw);

// The terrain and map-feature symbols are real public-domain drawings
// (FM 21-31, USGS) re-textured through config; no SQF kernel is needed.
// The registry is loaded in XEH_preInit.sqf.
