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

// Eye adaptation (issue #141): AEE owns the camera aperture and its rate.
PREPS(eye,eyeMesopicWeight);
PREPS(eye,eyePupilSteady);
PREPS(eye,eyePupilStep);
PREPS(eye,eyeAdaptStep);
PREPS(eye,eyeAdaptInit);
PREPS(eye,eyeAdaptState);
PREPS(eye,eyeLimits);
PREPS(eye,eyeSceneLux);
PREPS(eye,eyeAmbientLux);
PREPS(eye,eyeLocalLux);
PREPS(eye,eyeSkyFraction);
PREPS(eye,eyeSkyCast);
PREPS(eye,eyeAperture);
PREPS(eye,eyeSampleScene);
PREPS(eye,eyeFlash);
PREPS(eye,updateEyeAdaptation);
PREPS(eye,initEyeAdaptation);

PREPS(vision,managePostProcess);
PREPS(vision,teardownSensors);
PREPS(vision,runThermalPass);
PREPS(vision,enterThermalSensors);
PREPS(vision,exitThermalSensors);
PREPS(vision,updateThermalHost);
PREPS(vision,updateThermalHostSetting);
PREPS(vision,dtvHostTick);
PREPS(vision,dtvHostStart);
PREPS(vision,dtvHostStop);
PREPS(vision,calculateViewDistance);
// Scene-aware shadow distance (aee-workshop-copy item 6).
PREPS(vision,shadowSamplePattern);
PREPS(vision,shadowClassifyScene);
PREPS(vision,shadowTargetDistance);
PREPS(vision,shadowSmoothDistance);
PREPS(vision,shadowFpsGovernor);
PREPS(vision,shadowStabilizeDepth);
PREPS(vision,ppEffectCreate);
PREPS(vision,destroyBasePostProcess);
PREPS(vision,weatherGrainParams);
PREPS(vision,applyWeatherGrain);
PREPS(vision,initWeatherGrain);

// Grade (image realism): the normal-vision base grade and acuity pass.
PREPS(grade,baseGradeParams);
PREPS(grade,applyBaseGrade);
PREPS(grade,initBaseGrade);
PREPS(grade,teardownBaseGrade);

// Perception (human-vision model): the pure tone and composition kernels.
PREPS(perception,perceptionToneResponse);
PREPS(perception,perceptionIlluminant);
PREPS(perception,perceptionChromaticAdaptation);
PREPS(perception,perceptionMesopicColor);
PREPS(perception,perceptionBaseGrade);
PREPS(perception,perceptionParams);
PREPS(perception,perceptionSample);
PREPS(perception,perceptionAdaptState);
PREPS(perception,perceptionUpdate);
PREPS(perception,perceptionDetectDeviation);

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
PREPS(symbology,symbologyMarkers);
PREPS(symbology,symbologyMarkersApply);
PREPS(symbology,symbologyMarkersRestore);
PREPS(symbology,symbologyWorldDraw);

// The terrain and map-feature symbols are real public-domain drawings
// (FM 21-31, USGS) re-textured through config; no SQF kernel is needed.
// The registry is loaded in XEH_preInit.sqf.
