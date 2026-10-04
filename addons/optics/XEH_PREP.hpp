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
PREPS(eye,eyeSceneLux);
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
PREPS(vision,ppEffectCreate);
PREPS(vision,destroyBasePostProcess);

// Grade (image realism): the normal-vision base grade and acuity pass.
PREPS(grade,baseGradeParams);

PREPS(hud,hudBuild);
PREPS(hud,hudFormatGrid);
PREPS(hud,hudFormatHeading);
PREPS(hud,hudFormatRange);
PREPS(hud,hudMarkers);
PREPS(hud,hudRangefinder);
PREPS(hud,hudUpdate);
