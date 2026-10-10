---
title: "AEE extension contract"
---

# AEE extension contract

ADR-027 makes AEE's public surface a stable contract. AEE owns by declaration
and load order, not by force. A third-party mod consumes AEE by declaring it as
a dependency and loading after it. This note is the contract: the names AEE
guarantees, and the mechanism that lets another mod extend AEE without AEE
naming it.

## Dependency inversion

A mod extends AEE the way AEE extends a host mod. It declares AEE in its
`CfgPatches`:

```cpp
class CfgPatches {
    class my_mod {
        // The addon init order is the requiredAddons order (the CfgPatches
        // class name, not the PBO name). AEE loads first, so my_mod loads
        // after AEE and merges over it.
        requiredAddons[] = {"aee_core", "aee_lib"};
        skipWhenMissingDependencies = 1;
    };
};
```

`aee_core` always loads first in the AEE set, so it is the correct anchor. The
extension mod then:

- re-declares an engine class AEE owns, restating the true parent so the
  reopen merges instead of stripping inheritance, or
- calls an `aee_*` function, or
- reads an `aee_core_*` state variable, or
- registers into an AEE registry.

## The resolver registry template

The physiology resolver registries are the template for the last point, and the
general pattern for any AEE extension:

```sqf
private _resolvers = missionNamespace getVariable ["aee_physiology_massResolvers", []];
_resolvers pushBackUnique my_mod_fnc_itemMass;
missionNamespace setVariable ["aee_physiology_massResolvers", _resolvers];
```

AEE reads the registry and never names the extending mod:

```sqf
// addons/clothing/functions/clothing/fnc_getInventoryLoad.sqf
private _resolvers = missionNamespace getVariable [QGVAR(massResolvers), []];
```

The direction inverts onto AEE's registry: the core asks whether a resolver
exists and never names the host. `compat_ace3` registers into
`aee_physiology_massResolvers` and `aee_physiology_categoryResolvers` this way.
An extension mod registers into the same two lists, or copies the pattern with
its own `aee_<component>_*Resolvers` variable declared in the contract below.

## What AEE guarantees

- **The class namespace.** AEE declares config classes under `AEE_*` and
  `ColorAEE`, and AEE-authored classes such as `CfgClothing`. A mod that
  re-declares one of these wins if it loads after AEE; that is the ceiling.
- **The function namespace.** Every `aee_<component>_fnc_<name>` function is a
  compiled missionNamespace variable. First compile owns the name; a mod that
  recompiles it takes it over.
- **The state namespace.** Shared state is `aee_core_*`. AEE writes it; any mod
  or mission reads it. Addon-local state is `aee_<component>_*`.
- **The addon set.** The PBOs are `aee_<component>`. `aee_core` is the anchor
  to depend on.

The generated lists below are the enumerated contract, checked against the
source by `tools/gen_extension_contract.py --check`.

<!-- BEGIN GENERATED: extension contract -->

### Public addon PBOs

| PBO | Component |
|---|---|
| `aee_actions` | `actions` |
| `aee_ai` | `ai` |
| `aee_altitude` | `altitude` |
| `aee_ambience` | `ambience` |
| `aee_armour` | `armour` |
| `aee_atmos` | `atmos` |
| `aee_ballistics` | `ballistics` |
| `aee_blast` | `blast` |
| `aee_cartography` | `cartography` |
| `aee_clothing` | `clothing` |
| `aee_compat_ace3` | `compat_ace3` |
| `aee_compat_acm` | `compat_acm` |
| `aee_compat_acre2` | `compat_acre2` |
| `aee_compat_kat` | `compat_kat` |
| `aee_compat_realweather` | `compat_realweather` |
| `aee_compat_tfar` | `compat_tfar` |
| `aee_core` | `core` |
| `aee_diagnostics` | `diagnostics` |
| `aee_dive` | `dive` |
| `aee_eye` | `eye` |
| `aee_flight` | `flight` |
| `aee_hud` | `hud` |
| `aee_hydrology` | `hydrology` |
| `aee_lib` | `lib` |
| `aee_lighting` | `lighting` |
| `aee_ltm` | `ltm` |
| `aee_magnetism` | `magnetism` |
| `aee_maritime` | `maritime` |
| `aee_material` | `material` |
| `aee_mobility` | `mobility` |
| `aee_nightvision` | `nightvision` |
| `aee_optics` | `optics` |
| `aee_particles` | `particles` |
| `aee_persistence` | `persistence` |
| `aee_physiology` | `physiology` |
| `aee_radio` | `radio` |
| `aee_strain` | `strain` |
| `aee_symbology` | `symbology` |
| `aee_thermal` | `thermal` |
| `aee_thermal_display` | `thermal_display` |
| `aee_vehicles` | `vehicles` |
| `aee_vision` | `vision` |
| `aee_weather` | `weather` |
| `aee_weatherfx` | `weatherfx` |
| `aee_wildlife` | `wildlife` |

### Public functions (660)

Compiled by CBA XEH `PREP`/`PREPS` into the `aee_<component>_fnc_<name>` namespace. Call one as `call aee_<component>_fnc_<name>`.

- `aee_actions_fnc_calculateWeatherReport`
- `aee_actions_fnc_dumpState`
- `aee_actions_fnc_openAltimeter`
- `aee_actions_fnc_openWeatherReport`
- `aee_ai_fnc_agentDecide`
- `aee_ai_fnc_agentRegister`
- `aee_ai_fnc_agentSense`
- `aee_ai_fnc_agentUnregister`
- `aee_ai_fnc_aiTick`
- `aee_ai_fnc_aiTickPFH`
- `aee_ai_fnc_disturbanceApply`
- `aee_ai_fnc_disturbanceKey`
- `aee_ai_fnc_disturbancePrune`
- `aee_ai_fnc_disturbanceSample`
- `aee_ai_fnc_dumpState`
- `aee_ai_fnc_initAI`
- `aee_ai_fnc_receiveStimulus`
- `aee_ai_fnc_reportStimulus`
- `aee_ai_fnc_stimulusDecay`
- `aee_ai_fnc_teardownAI`
- `aee_altitude_fnc_calculateAltitudeAcclimatization`
- `aee_altitude_fnc_calculateAltitudeDCS`
- `aee_altitude_fnc_calculateBarometricPressure`
- `aee_altitude_fnc_calculateGLOC`
- `aee_altitude_fnc_calculateHypoxia`
- `aee_altitude_fnc_calculateOxygenDelivery`
- `aee_ambience_fnc_acousticLevel`
- `aee_ambience_fnc_acousticOccluders`
- `aee_ambience_fnc_acousticPublish`
- `aee_ambience_fnc_acousticSample`
- `aee_ambience_fnc_acousticSourceDb`
- `aee_ambience_fnc_callEmit`
- `aee_ambience_fnc_callPitch`
- `aee_ambience_fnc_callPublish`
- `aee_ambience_fnc_callReceive`
- `aee_ambience_fnc_callSample`
- `aee_ambience_fnc_disturbanceSilence`
- `aee_ambience_fnc_emitterClass`
- `aee_ambience_fnc_emitterPlan`
- `aee_ambience_fnc_emitterRelease`
- `aee_ambience_fnc_emitterSync`
- `aee_ambience_fnc_getCallPattern`
- `aee_ambience_fnc_playAmbientBed`
- `aee_ambience_fnc_playOneShot`
- `aee_ambience_fnc_shotAudio`
- `aee_ambience_fnc_soundBedForContext`
- `aee_ambience_fnc_soundTick`
- `aee_ambience_fnc_speciesSound`
- `aee_armour_fnc_deriveProtection`
- `aee_armour_fnc_dumpState`
- `aee_armour_fnc_getVehicleArmour`
- `aee_armour_fnc_penetrationGate`
- `aee_atmos_fnc_calculateAirframeIcing`
- `aee_atmos_fnc_calculateCloudCeiling`
- `aee_atmos_fnc_calculateCloudDevelopment`
- `aee_atmos_fnc_calculateHailEnergy`
- `aee_atmos_fnc_calculateHalo`
- `aee_atmos_fnc_calculateHaze`
- `aee_atmos_fnc_calculateLightning`
- `aee_atmos_fnc_calculateMicroburst`
- `aee_atmos_fnc_calculateOrographicPrecipitation`
- `aee_atmos_fnc_calculatePrecipitationPhase`
- `aee_atmos_fnc_calculatePressureTrend`
- `aee_atmos_fnc_calculateRefraction`
- `aee_atmos_fnc_calculateRelativeHumidity`
- `aee_atmos_fnc_calculateStationPressure`
- `aee_atmos_fnc_calculateTerrainWind`
- `aee_atmos_fnc_calculateTurbulence`
- `aee_atmos_fnc_dumpState`
- `aee_atmos_fnc_getLocalWind`
- `aee_atmos_fnc_hailDamage`
- `aee_atmos_fnc_updateEngineLightnings`
- `aee_atmos_fnc_updateFog`
- `aee_atmos_fnc_updateHumidity`
- `aee_atmos_fnc_updateLocalWindParams`
- `aee_atmos_fnc_updatePressure`
- `aee_atmos_fnc_updateRainbow`
- `aee_atmos_fnc_updateSimulWeatherLayers`
- `aee_atmos_fnc_updateWind`
- `aee_ballistics_fnc_calculateAirDensity`
- `aee_ballistics_fnc_calculateAirDensityKernel`
- `aee_ballistics_fnc_calculateAmmoTemperature`
- `aee_ballistics_fnc_calculateBallisticCoefficient`
- `aee_ballistics_fnc_calculateBallisticDrag`
- `aee_ballistics_fnc_calculateBarrelState`
- `aee_ballistics_fnc_calculateCoriolisDeflection`
- `aee_ballistics_fnc_calculateCrosswindBallistics`
- `aee_ballistics_fnc_calculateInteriorBallistics`
- `aee_ballistics_fnc_calculateMachCone`
- `aee_ballistics_fnc_calculateMuzzleVelocityCorrection`
- `aee_ballistics_fnc_calculatePropellantSensitivity`
- `aee_ballistics_fnc_calculateRecoil`
- `aee_ballistics_fnc_calculateStability`
- `aee_ballistics_fnc_calculateSupersonicTrace`
- `aee_ballistics_fnc_deriveCartridge`
- `aee_ballistics_fnc_dumpState`
- `aee_ballistics_fnc_getBulletShape`
- `aee_ballistics_fnc_getCartridgeBands`
- `aee_ballistics_fnc_getCartridgeData`
- `aee_ballistics_fnc_getDragTables`
- `aee_ballistics_fnc_getEnvironmentState`
- `aee_ballistics_fnc_getLoadData`
- `aee_ballistics_fnc_getProjectileBands`
- `aee_ballistics_fnc_getProjectileData`
- `aee_ballistics_fnc_getWeaponBands`
- `aee_ballistics_fnc_getWeaponData`
- `aee_ballistics_fnc_measureBarrel`
- `aee_ballistics_fnc_parseCaliber`
- `aee_ballistics_fnc_resolveShot`
- `aee_ballistics_fnc_selectBand`
- `aee_ballistics_fnc_startStateDump`
- `aee_blast_fnc_calculateBlastInjury`
- `aee_blast_fnc_calculateBlastOverpressure`
- `aee_cartography_fnc_fontFamilyUsable`
- `aee_cartography_fnc_formatGridDisplay`
- `aee_cartography_fnc_gpsBuild`
- `aee_cartography_fnc_gpsUpdate`
- `aee_cartography_fnc_hudFormatGrid`
- `aee_cartography_fnc_mapIconWorldSize`
- `aee_cartography_fnc_mgrsCursorText`
- `aee_cartography_fnc_mgrsEffectivePrecision`
- `aee_cartography_fnc_mgrsFontFamily`
- `aee_cartography_fnc_mgrsGridLines`
- `aee_cartography_fnc_mgrsMapDraw`
- `aee_cartography_fnc_mgrsMapPrecision`
- `aee_cartography_fnc_mgrsMarkerText`
- `aee_clothing_fnc_getCamouflageProperties`
- `aee_clothing_fnc_getEquipmentBands`
- `aee_clothing_fnc_getEquipmentProperties`
- `aee_clothing_fnc_getGloveProperties`
- `aee_clothing_fnc_getGoggleProperties`
- `aee_clothing_fnc_getHelmetProperties`
- `aee_clothing_fnc_getInventoryLoad`
- `aee_clothing_fnc_getItemMass`
- `aee_clothing_fnc_getMagazineLoad`
- `aee_clothing_fnc_getMagazineMass`
- `aee_clothing_fnc_getNirPerSelection`
- `aee_clothing_fnc_getNvgContrast`
- `aee_clothing_fnc_getPackProperties`
- `aee_clothing_fnc_getUniformProperties`
- `aee_clothing_fnc_getVestProperties`
- `aee_clothing_fnc_getWeaponLoad`
- `aee_clothing_fnc_getWeaponMass`
- `aee_clothing_fnc_selectBand`
- `aee_compat_ace3_fnc_dumpState`
- `aee_compat_ace3_fnc_getAceItemMass`
- `aee_compat_ace3_fnc_integrateKestrel`
- `aee_compat_ace3_fnc_integrateMedical`
- `aee_compat_ace3_fnc_isAceMedicalItem`
- `aee_compat_acm_fnc_integrateACM`
- `aee_compat_acm_fnc_registerHypoxiaDutyFactor`
- `aee_compat_acre2_fnc_integrateACRE2`
- `aee_compat_kat_fnc_integrateKAT`
- `aee_compat_realweather_fnc_dumpState`
- `aee_compat_realweather_fnc_integrateRealWeather`
- `aee_compat_tfar_fnc_integrateTFAR`
- `aee_core_fnc_calculateIlluminance`
- `aee_core_fnc_calculateSeededWeatherProgression`
- `aee_core_fnc_coreBodyTemp`
- `aee_core_fnc_dispatchKernel`
- `aee_core_fnc_getEyeState`
- `aee_core_fnc_getSmoothedWeather`
- `aee_core_fnc_handleCollisionDamage`
- `aee_core_fnc_init`
- `aee_core_fnc_initKernelTable`
- `aee_core_fnc_moduleInit`
- `aee_core_fnc_moduleStormInit`
- `aee_core_fnc_probeExtension`
- `aee_core_fnc_updateEnvironment`
- `aee_core_fnc_updateSimClock`
- `aee_diagnostics_fnc_consistencyFailureLine`
- `aee_diagnostics_fnc_consistencyLoadTable`
- `aee_diagnostics_fnc_consistencyLog`
- `aee_diagnostics_fnc_diagnostic`
- `aee_diagnostics_fnc_dumpPerformanceCounters`
- `aee_diagnostics_fnc_dumpState`
- `aee_diagnostics_fnc_evaluateConsistency`
- `aee_diagnostics_fnc_reportModuleHealth`
- `aee_diagnostics_fnc_runConsistencyCheck`
- `aee_dive_fnc_getDiveState`
- `aee_dive_fnc_updateDiveState`
- `aee_eye_fnc_eyeAdaptInit`
- `aee_eye_fnc_eyeAdaptState`
- `aee_eye_fnc_eyeAdaptStep`
- `aee_eye_fnc_eyeAmbientLux`
- `aee_eye_fnc_eyeAperture`
- `aee_eye_fnc_eyeFlash`
- `aee_eye_fnc_eyeFlashScene`
- `aee_eye_fnc_eyeLimits`
- `aee_eye_fnc_eyeLocalLux`
- `aee_eye_fnc_eyeMesopicWeight`
- `aee_eye_fnc_eyePupilSteady`
- `aee_eye_fnc_eyePupilStep`
- `aee_eye_fnc_eyeSampleScene`
- `aee_eye_fnc_eyeSceneLux`
- `aee_eye_fnc_eyeSkyCast`
- `aee_eye_fnc_eyeSkyFraction`
- `aee_eye_fnc_eyeTimeSkip`
- `aee_eye_fnc_initEyeAdaptation`
- `aee_eye_fnc_updateEyeAdaptation`
- `aee_flight_fnc_applyAirframeLoad`
- `aee_flight_fnc_applyFlightTurbulence`
- `aee_flight_fnc_calculateAeroPenalty`
- `aee_flight_fnc_calculateAirEngineLoad`
- `aee_flight_fnc_calculateEngineNg`
- `aee_flight_fnc_calculateFuelBurn`
- `aee_flight_fnc_calculateHelicopterLift`
- `aee_flight_fnc_calculateScriptedTgtOil`
- `aee_flight_fnc_calculateTurbulenceForce`
- `aee_flight_fnc_getAircraftData`
- `aee_flight_fnc_getAircraftMatch`
- `aee_flight_fnc_getAircraftSystems`
- `aee_flight_fnc_logAirframeState`
- `aee_flight_fnc_resolveFlightModel`
- `aee_flight_fnc_resolveTurbulenceArea`
- `aee_flight_fnc_updateAircraftSystems`
- `aee_flight_fnc_updateDamageSystem`
- `aee_flight_fnc_updateEngineSystem`
- `aee_flight_fnc_updateFuelSystem`
- `aee_flight_fnc_updateStatusSystems`
- `aee_hud_fnc_hudBuild`
- `aee_hud_fnc_hudFormatHeading`
- `aee_hud_fnc_hudFormatRange`
- `aee_hud_fnc_hudMarkers`
- `aee_hud_fnc_hudRangefinder`
- `aee_hud_fnc_hudUpdate`
- `aee_hud_fnc_trackerDraw`
- `aee_hud_fnc_trackerProject`
- `aee_hud_fnc_trackerUpdate`
- `aee_hydrology_fnc_calculateBaseflow`
- `aee_hydrology_fnc_calculateDepressionStorage`
- `aee_hydrology_fnc_calculateGreenAmptInfiltration`
- `aee_hydrology_fnc_calculateRiverWaterLevel`
- `aee_hydrology_fnc_calculateRunoffSCS`
- `aee_hydrology_fnc_calculateThermalRefraction`
- `aee_hydrology_fnc_routeRunoffD8`
- `aee_lib_fnc_attachObjectEngineHandler`
- `aee_lib_fnc_buildGeoAnchor`
- `aee_lib_fnc_createPPEffect`
- `aee_lib_fnc_datalinkState`
- `aee_lib_fnc_destroyPPEffect`
- `aee_lib_fnc_deterministicRandom`
- `aee_lib_fnc_evaluateGeoConsistency`
- `aee_lib_fnc_formatMgrs`
- `aee_lib_fnc_getGeoAnchor`
- `aee_lib_fnc_getWorldLocation`
- `aee_lib_fnc_gnssErrorEllipse`
- `aee_lib_fnc_gnssFixState`
- `aee_lib_fnc_installObjectEngineHandler`
- `aee_lib_fnc_installPlayerEngineHandler`
- `aee_lib_fnc_latLonToUtm`
- `aee_lib_fnc_mgrsToWorld`
- `aee_lib_fnc_migrateLegacySettings`
- `aee_lib_fnc_parseMgrs`
- `aee_lib_fnc_readState`
- `aee_lib_fnc_runGeoConsistency`
- `aee_lib_fnc_utmToLatLon`
- `aee_lib_fnc_utmToWorld`
- `aee_lib_fnc_worldToMgrs`
- `aee_lighting_fnc_applyWorldLighting`
- `aee_lighting_fnc_calculateLimitingMagnitude`
- `aee_lighting_fnc_calculateSolarRadiation`
- `aee_lighting_fnc_classifyNight`
- `aee_lighting_fnc_drawFaintStars`
- `aee_lighting_fnc_drawMilkyWay`
- `aee_lighting_fnc_galacticToEquatorial`
- `aee_lighting_fnc_galacticToHorizontal`
- `aee_lighting_fnc_getStarCatalog`
- `aee_lighting_fnc_lightPollutionPenalty`
- `aee_lighting_fnc_logSkyState`
- `aee_lighting_fnc_meteorRate`
- `aee_lighting_fnc_meteorShowers`
- `aee_lighting_fnc_meteorState`
- `aee_lighting_fnc_radiantHorizontal`
- `aee_lighting_fnc_renderAurora`
- `aee_lighting_fnc_renderDynamicStars`
- `aee_lighting_fnc_renderMeteors`
- `aee_lighting_fnc_renderMilkyWay`
- `aee_lighting_fnc_showerIsActive`
- `aee_lighting_fnc_siderealTime`
- `aee_lighting_fnc_skyGateReason`
- `aee_lighting_fnc_starBrightnessCoefficient`
- `aee_lighting_fnc_starCatalogData`
- `aee_lighting_fnc_starDirection`
- `aee_lighting_fnc_starLightsSync`
- `aee_lighting_fnc_starMagnitude`
- `aee_lighting_fnc_starWeatherFade`
- `aee_lighting_fnc_updateAurora`
- `aee_lighting_fnc_updateMeteors`
- `aee_lighting_fnc_updateMilkyWay`
- `aee_lighting_fnc_worldLightingClass`
- `aee_lighting_fnc_worldLightingProfile`
- `aee_ltm_fnc_ltmBeamSegments`
- `aee_ltm_fnc_ltmCreate`
- `aee_ltm_fnc_ltmDaylightAlpha`
- `aee_ltm_fnc_ltmDraw`
- `aee_ltm_fnc_ltmInit`
- `aee_ltm_fnc_ltmPFH`
- `aee_ltm_fnc_ltmToggle`
- `aee_ltm_fnc_ltmToggleMode`
- `aee_magnetism_fnc_calculateCompassDeviation`
- `aee_magnetism_fnc_calculateMagneticAnomaly`
- `aee_maritime_fnc_calculateSeaState`
- `aee_maritime_fnc_calculateSeaSurfaceTemperature`
- `aee_maritime_fnc_calculateTidalPrediction`
- `aee_maritime_fnc_dumpState`
- `aee_maritime_fnc_updateEngineWaves`
- `aee_material_fnc_calculateStefanCoefficient`
- `aee_material_fnc_classifyBySurfaceType`
- `aee_material_fnc_dumpState`
- `aee_material_fnc_getObjectMaterial`
- `aee_material_fnc_getSurfaceMaterial`
- `aee_material_fnc_handleHitPart`
- `aee_material_fnc_initMaterialCache`
- `aee_mobility_fnc_applyAccretionMass`
- `aee_mobility_fnc_applyGripLoss`
- `aee_mobility_fnc_applyRollover`
- `aee_mobility_fnc_applyTerrainDrag`
- `aee_mobility_fnc_calculateAccretionMass`
- `aee_mobility_fnc_calculateMudAccretion`
- `aee_mobility_fnc_calculateRolloverThreshold`
- `aee_mobility_fnc_calculateRouteDegradation`
- `aee_mobility_fnc_calculateSSF`
- `aee_mobility_fnc_calculateSoilBearingStrength`
- `aee_mobility_fnc_calculateSoilStrength`
- `aee_mobility_fnc_calculateTerrainLimits`
- `aee_mobility_fnc_calculateTraction`
- `aee_mobility_fnc_calculateWetTraction`
- `aee_mobility_fnc_getTerrainSpeedFactor`
- `aee_mobility_fnc_updateGroundState`
- `aee_nightvision_fnc_applyNVGTubeModel`
- `aee_nightvision_fnc_applyNightGrain`
- `aee_nightvision_fnc_dumpState`
- `aee_nightvision_fnc_getDeviceData`
- `aee_nightvision_fnc_getDeviceMatch`
- `aee_nightvision_fnc_getNvgDeviceProperties`
- `aee_nightvision_fnc_getNvgTubeModel`
- `aee_nightvision_fnc_nvgAgcBreathing`
- `aee_nightvision_fnc_nvgBlemishField`
- `aee_nightvision_fnc_nvgBlindingEnvelope`
- `aee_nightvision_fnc_nvgPincushion`
- `aee_nightvision_fnc_nvgScintillation`
- `aee_nightvision_fnc_nvgTierIndex`
- `aee_nightvision_fnc_teardownNvgDoF`
- `aee_optics_fnc_applyAtmosphericSeeingFX`
- `aee_optics_fnc_applyDewOnOpticsFX`
- `aee_optics_fnc_applyHeatShimmerFX`
- `aee_optics_fnc_applyMirageFX`
- `aee_optics_fnc_applyRainOnOpticsFX`
- `aee_optics_fnc_applySnowBlindnessFX`
- `aee_optics_fnc_applySolarGlareFX`
- `aee_optics_fnc_calculateAtmosphericSeeing`
- `aee_optics_fnc_calculateAttenuation`
- `aee_optics_fnc_calculateDewOnOptics`
- `aee_optics_fnc_calculateGreenFlash`
- `aee_optics_fnc_calculateMirageIntensity`
- `aee_optics_fnc_calculatePrecipitationVisibility`
- `aee_optics_fnc_calculateRainOnOptics`
- `aee_optics_fnc_calculateSmokePersistence`
- `aee_optics_fnc_calculateSnowBlindness`
- `aee_optics_fnc_calculateSolarGlare`
- `aee_optics_fnc_calculateVehicleHeatShimmer`
- `aee_optics_fnc_dumpState`
- `aee_optics_fnc_getOpticProperties`
- `aee_particles_fnc_calculateDownwash`
- `aee_particles_fnc_dumpState`
- `aee_particles_fnc_heatHazeAlpha`
- `aee_particles_fnc_heatHazeSize`
- `aee_particles_fnc_kickupParams`
- `aee_particles_fnc_particleAllocate`
- `aee_particles_fnc_particleEffectConfig`
- `aee_particles_fnc_particleEmission`
- `aee_particles_fnc_particleMaterial`
- `aee_particles_fnc_particlePipeline`
- `aee_particles_fnc_particlePipelineEmit`
- `aee_particles_fnc_particleState`
- `aee_particles_fnc_registerParticleSource`
- `aee_particles_fnc_renderSupersonicTrace`
- `aee_particles_fnc_surfaceMaterial`
- `aee_particles_fnc_surfaceSample`
- `aee_particles_fnc_weatherParticleAlpha`
- `aee_persistence_fnc_calculateAvalancheRisk`
- `aee_persistence_fnc_calculateCBRNPersistence`
- `aee_persistence_fnc_calculateFireSpreadRisk`
- `aee_persistence_fnc_calculateFlashFloodRisk`
- `aee_persistence_fnc_calculateFreezeThawCycling`
- `aee_persistence_fnc_calculateFrostOnWindscreens`
- `aee_persistence_fnc_calculateIceLoad`
- `aee_persistence_fnc_calculateSurfaceWetness`
- `aee_persistence_fnc_detectGroundFrost`
- `aee_persistence_fnc_getCbrnProtection`
- `aee_persistence_fnc_updateSoilMoisture`
- `aee_physiology_fnc_applyHeatStressHUD`
- `aee_physiology_fnc_dumpState`
- `aee_physiology_fnc_updateFatigueState`
- `aee_physiology_fnc_zh16cStep`
- `aee_radio_fnc_calculateIonosphericAbsorption`
- `aee_radio_fnc_calculateRadioPropagation`
- `aee_radio_fnc_dumpState`
- `aee_strain_fnc_applyCrossSensitivity`
- `aee_strain_fnc_applyMovementSpeed`
- `aee_strain_fnc_calculateColdWeatherPerformance`
- `aee_strain_fnc_calculateDehydrationRisk`
- `aee_strain_fnc_calculateFatigueFactor`
- `aee_strain_fnc_calculateShooterStability`
- `aee_strain_fnc_calculateSleepPressure`
- `aee_strain_fnc_calculateUVIndex`
- `aee_strain_fnc_getGLoad`
- `aee_strain_fnc_integrateSwayFactor`
- `aee_symbology_fnc_symbolCategory`
- `aee_symbology_fnc_symbolFrame`
- `aee_symbology_fnc_symbolIcon`
- `aee_symbology_fnc_symbolPalette`
- `aee_symbology_fnc_symbolResolve`
- `aee_symbology_fnc_symbologyAffiliation`
- `aee_symbology_fnc_symbologyDimension`
- `aee_symbology_fnc_symbologyEchelon`
- `aee_symbology_fnc_symbologyEchelonMarker`
- `aee_symbology_fnc_symbologyEchelonSize`
- `aee_symbology_fnc_symbologyHasTracker`
- `aee_symbology_fnc_symbologyKilledMarker`
- `aee_symbology_fnc_symbologyMarkerCategory`
- `aee_symbology_fnc_symbologyMarkerColor`
- `aee_symbology_fnc_symbologyMarkerType`
- `aee_symbology_fnc_symbologyMarkers`
- `aee_symbology_fnc_symbologyMarkersApply`
- `aee_symbology_fnc_symbologyMarkersRestore`
- `aee_symbology_fnc_symbologyPaletteFriendly`
- `aee_symbology_fnc_symbologyUnitCategory`
- `aee_symbology_fnc_symbologyUnitDimension`
- `aee_symbology_fnc_symbologyUnitEchelon`
- `aee_symbology_fnc_symbologyWorldDraw`
- `aee_thermal_display_fnc_activeIRGate`
- `aee_thermal_display_fnc_applyActiveIR`
- `aee_thermal_display_fnc_applyFusionFill`
- `aee_thermal_display_fnc_applyFusionOverlay`
- `aee_thermal_display_fnc_applyFusionPP`
- `aee_thermal_display_fnc_applyFusionSun`
- `aee_thermal_display_fnc_applyThermalVision`
- `aee_thermal_display_fnc_createThermalPPEffects`
- `aee_thermal_display_fnc_cycleFusionMode`
- `aee_thermal_display_fnc_fusionBandIndex`
- `aee_thermal_display_fnc_fusionFovGate`
- `aee_thermal_display_fnc_fusionFrameGeometry`
- `aee_thermal_display_fnc_fusionFrameVisible`
- `aee_thermal_display_fnc_fusionGateDecision`
- `aee_thermal_display_fnc_fusionMaterialPaths`
- `aee_thermal_display_fnc_fusionThermalField`
- `aee_thermal_display_fnc_hudBoxDraw`
- `aee_thermal_display_fnc_hudTapeActive`
- `aee_thermal_display_fnc_hudTapeBoot`
- `aee_thermal_display_fnc_hudTapeBuild`
- `aee_thermal_display_fnc_hudTapeDraw`
- `aee_thermal_display_fnc_hudTapeInfo`
- `aee_thermal_display_fnc_isFusionCapable`
- `aee_thermal_display_fnc_outlineCanvas`
- `aee_thermal_display_fnc_outlineCollect`
- `aee_thermal_display_fnc_outlineDraw`
- `aee_thermal_display_fnc_outlineGearRadius`
- `aee_thermal_display_fnc_outlineSensorLod`
- `aee_thermal_display_fnc_outlineSkeleton`
- `aee_thermal_display_fnc_outlineToggle`
- `aee_thermal_display_fnc_outlineTopo`
- `aee_thermal_display_fnc_resolveFusionDevice`
- `aee_thermal_display_fnc_startActiveIR`
- `aee_thermal_display_fnc_stopActiveIR`
- `aee_thermal_display_fnc_thermalImperfectionParams`
- `aee_thermal_display_fnc_thermalPalette`
- `aee_thermal_display_fnc_thermalResolutionParams`
- `aee_thermal_display_fnc_thermalWetDistortionParams`
- `aee_thermal_display_fnc_updateFusionFrame`
- `aee_thermal_display_fnc_warmThermalPPEffects`
- `aee_thermal_fnc_addGroundStamp`
- `aee_thermal_fnc_applyBuildingThermal`
- `aee_thermal_fnc_applyClothingThermal`
- `aee_thermal_fnc_applyContactConduction`
- `aee_thermal_fnc_applyEngineThermal`
- `aee_thermal_fnc_applyExhaustHeat`
- `aee_thermal_fnc_applyGroundContactStamps`
- `aee_thermal_fnc_applyImpactHeat`
- `aee_thermal_fnc_applyRadiativeExchange`
- `aee_thermal_fnc_applyRainDroplets`
- `aee_thermal_fnc_applySecondSun`
- `aee_thermal_fnc_applySelectionThermal`
- `aee_thermal_fnc_applyWeaponBarrelHeat`
- `aee_thermal_fnc_calculateAtmosphericTransmission`
- `aee_thermal_fnc_calculateBandRadiance`
- `aee_thermal_fnc_calculateBatteryTemperatureDerating`
- `aee_thermal_fnc_calculateClothingInsulation`
- `aee_thermal_fnc_calculateFreezingRain`
- `aee_thermal_fnc_calculateFrostState`
- `aee_thermal_fnc_calculateGlobeTemperature`
- `aee_thermal_fnc_calculateGroundNodeStack`
- `aee_thermal_fnc_calculateGroundTemperature`
- `aee_thermal_fnc_calculateHeatIndex`
- `aee_thermal_fnc_calculateHypothermiaRisk`
- `aee_thermal_fnc_calculateMRT`
- `aee_thermal_fnc_calculateObjectTemperature`
- `aee_thermal_fnc_calculateReflectedSolarBand`
- `aee_thermal_fnc_calculateSensorThreshold`
- `aee_thermal_fnc_calculateSkyRadiance`
- `aee_thermal_fnc_calculateThermalContrast`
- `aee_thermal_fnc_calculateThermalCrossover`
- `aee_thermal_fnc_calculateThermalNoise`
- `aee_thermal_fnc_calculateUnitLoadoutThermal`
- `aee_thermal_fnc_calculateVehicleHeat`
- `aee_thermal_fnc_calculateWBGT`
- `aee_thermal_fnc_calculateWaterTemperature`
- `aee_thermal_fnc_collectThermalNestedObjects`
- `aee_thermal_fnc_dumpState`
- `aee_thermal_fnc_evaluateThermalEdge`
- `aee_thermal_fnc_expandThermalSelectionTree`
- `aee_thermal_fnc_getEffectiveEmissivity`
- `aee_thermal_fnc_getGroundStampOffset`
- `aee_thermal_fnc_getHitPointMaterials`
- `aee_thermal_fnc_getMaterialThermal`
- `aee_thermal_fnc_getNearestSelection`
- `aee_thermal_fnc_getSelectionMaterials`
- `aee_thermal_fnc_getSelectionSunExposure`
- `aee_thermal_fnc_getSolarAbsorptance`
- `aee_thermal_fnc_getThermalDeviceProperties`
- `aee_thermal_fnc_getThermalNestedObjects`
- `aee_thermal_fnc_getThermalSelectionLag`
- `aee_thermal_fnc_getThermalSelectionNames`
- `aee_thermal_fnc_getThermalSelectionPoints`
- `aee_thermal_fnc_getThermalSelections`
- `aee_thermal_fnc_handleImpactHeat`
- `aee_thermal_fnc_isPositionShadowed`
- `aee_thermal_fnc_isThermalHostActive`
- `aee_thermal_fnc_planckBandRadiance`
- `aee_thermal_fnc_probeThermalCapability`
- `aee_thermal_fnc_resolvePaintIndexFromSelections`
- `aee_thermal_fnc_resolveSelectionPaintIndex`
- `aee_thermal_fnc_resolveThermalBand`
- `aee_thermal_fnc_resolveThermalTarget`
- `aee_thermal_fnc_resolveThermalVisibility`
- `aee_thermal_fnc_solarElevation`
- `aee_thermal_fnc_solveTwoNodeKernel`
- `aee_thermal_fnc_solveTwoNodeSelection`
- `aee_thermal_fnc_takeThermalSweep`
- `aee_thermal_fnc_updateTemperature`
- `aee_thermal_fnc_updateThermalAGC`
- `aee_vehicles_fnc_calculateEngineLoad`
- `aee_vehicles_fnc_calculateEnginePower`
- `aee_vehicles_fnc_calculateExhaustPlume`
- `aee_vehicles_fnc_classifyVehicle`
- `aee_vehicles_fnc_estimateVehicleMass`
- `aee_vehicles_fnc_estimateVehicleMassCore`
- `aee_vehicles_fnc_getNearbyVehicles`
- `aee_vehicles_fnc_getVehicleBands`
- `aee_vehicles_fnc_getVehicleData`
- `aee_vehicles_fnc_getVehicleGeometry`
- `aee_vehicles_fnc_getVehicleMassModel`
- `aee_vehicles_fnc_getVehicleMatch`
- `aee_vision_fnc_applyBaseGrade`
- `aee_vision_fnc_applyWeatherGrain`
- `aee_vision_fnc_baseGradeParams`
- `aee_vision_fnc_calculateViewDistance`
- `aee_vision_fnc_destroyBasePostProcess`
- `aee_vision_fnc_dtvHostStart`
- `aee_vision_fnc_dtvHostStop`
- `aee_vision_fnc_dtvHostTick`
- `aee_vision_fnc_enterThermalSensors`
- `aee_vision_fnc_exitThermalSensors`
- `aee_vision_fnc_initBaseGrade`
- `aee_vision_fnc_initWeatherGrain`
- `aee_vision_fnc_managePostProcess`
- `aee_vision_fnc_perceptionAdaptState`
- `aee_vision_fnc_perceptionBaseGrade`
- `aee_vision_fnc_perceptionChromaticAdaptation`
- `aee_vision_fnc_perceptionDetectDeviation`
- `aee_vision_fnc_perceptionIlluminant`
- `aee_vision_fnc_perceptionMesopicColor`
- `aee_vision_fnc_perceptionParams`
- `aee_vision_fnc_perceptionSample`
- `aee_vision_fnc_perceptionToneResponse`
- `aee_vision_fnc_perceptionUpdate`
- `aee_vision_fnc_ppEffectCreate`
- `aee_vision_fnc_runThermalPass`
- `aee_vision_fnc_shadowClassifyScene`
- `aee_vision_fnc_shadowFpsGovernor`
- `aee_vision_fnc_shadowSamplePattern`
- `aee_vision_fnc_shadowSmoothDistance`
- `aee_vision_fnc_shadowStabilizeDepth`
- `aee_vision_fnc_shadowTargetDistance`
- `aee_vision_fnc_teardownBaseGrade`
- `aee_vision_fnc_teardownSensors`
- `aee_vision_fnc_updateThermalHost`
- `aee_vision_fnc_updateThermalHostSetting`
- `aee_vision_fnc_weatherGrainParams`
- `aee_weather_fnc_calculateBiologicalAmbient`
- `aee_weather_fnc_calculateBlowingSnowVisibility`
- `aee_weather_fnc_calculateConcealment`
- `aee_weather_fnc_calculateCropState`
- `aee_weather_fnc_calculateDustSuppression`
- `aee_weather_fnc_calculateDustVisibility`
- `aee_weather_fnc_calculateFogBaseAltitude`
- `aee_weather_fnc_calculateLunarIllumination`
- `aee_weather_fnc_calculateMicroclimate`
- `aee_weather_fnc_calculateQNH`
- `aee_weather_fnc_calculateScentDispersion`
- `aee_weather_fnc_calculateSevereWeather`
- `aee_weather_fnc_calculateSnowAccumulation`
- `aee_weather_fnc_calculateSpaceWeather`
- `aee_weather_fnc_calculateUrbanHeatIsland`
- `aee_weather_fnc_calculateWaterInfluence`
- `aee_weather_fnc_classifyBiome`
- `aee_weather_fnc_getBiome`
- `aee_weather_fnc_getBiomeAtPosition`
- `aee_weather_fnc_getBiomeName`
- `aee_weather_fnc_getClimateNormals`
- `aee_weather_fnc_getCoastDistance`
- `aee_weather_fnc_getLatitudeClimate`
- `aee_weather_fnc_getSmoothedBiome`
- `aee_weather_fnc_scanTerrainSignals`
- `aee_weather_fnc_updateBiomePosition`
- `aee_weather_fnc_updateSeasonalFoliage`
- `aee_weather_fnc_updateSoundPropagation`
- `aee_weatherfx_fnc_applyAtmosphericDust`
- `aee_weatherfx_fnc_applyBreathCondensation`
- `aee_weatherfx_fnc_applyExhaustShimmer`
- `aee_weatherfx_fnc_applyFootfallDust`
- `aee_weatherfx_fnc_applyRainSurfaceDrops`
- `aee_weatherfx_fnc_applyRainVehicleSound`
- `aee_weatherfx_fnc_applyRotorWash`
- `aee_weatherfx_fnc_applyVehicleDust`
- `aee_weatherfx_fnc_applyWeatherParticles`
- `aee_weatherfx_fnc_applyWindNoise`
- `aee_weatherfx_fnc_calculateLightningStrikeEffects`
- `aee_weatherfx_fnc_triggerLightning`
- `aee_weatherfx_fnc_triggerSevereWeatherFX`
- `aee_wildlife_fnc_applyAnimalBehaviour`
- `aee_wildlife_fnc_cullFauna`
- `aee_wildlife_fnc_ecologyBudget`
- `aee_wildlife_fnc_ecologyTick`
- `aee_wildlife_fnc_environmentGrid`
- `aee_wildlife_fnc_environmentSuitability`
- `aee_wildlife_fnc_getSeason`
- `aee_wildlife_fnc_getSpeciesMatch`
- `aee_wildlife_fnc_habitatBoundary`
- `aee_wildlife_fnc_initWildlife`
- `aee_wildlife_fnc_logWildlifeState`
- `aee_wildlife_fnc_monitorWildlife`
- `aee_wildlife_fnc_needsTick`
- `aee_wildlife_fnc_pickBedSource`
- `aee_wildlife_fnc_pickResourceTarget`
- `aee_wildlife_fnc_resourceScore`
- `aee_wildlife_fnc_sampleNeighbourhood`
- `aee_wildlife_fnc_spawnBudget`
- `aee_wildlife_fnc_spawnFauna`
- `aee_wildlife_fnc_speciesDeprecation`
- `aee_wildlife_fnc_speciesForBiome`
- `aee_wildlife_fnc_spookRange`
- `aee_wildlife_fnc_spookWave`
- `aee_wildlife_fnc_teardownWildlife`
- `aee_wildlife_fnc_vegScore`
- `aee_wildlife_fnc_wildlifePerceive`
- `aee_wildlife_fnc_wildlifeThink`
- `aee_wildlife_fnc_wildlifeTick`
- `aee_wildlife_fnc_wildlifeTickPFH`

### Public core state variables (56)

The `aee_core_*` mission variables. The canonical list of every published variable is `docs/wiki/chapters/state-variables.qmd`; these are the names that appear in the source as a contract surface.

- `aee_core_ambientLux`
- `aee_core_avgGroundTemp`
- `aee_core_biome`
- `aee_core_camoCoefficient`
- `aee_core_cbrnPersistence`
- `aee_core_clothingInsulation`
- `aee_core_consistencyFailures`
- `aee_core_consistencyState`
- `aee_core_coreBodyTemp`
- `aee_core_currentHeatIndex`
- `aee_core_currentHumidity`
- `aee_core_currentHypothermiaRisk`
- `aee_core_currentHypoxiaRisk`
- `aee_core_currentOvercast`
- `aee_core_currentSunElevation`
- `aee_core_currentTemperature`
- `aee_core_currentTemperatureBase`
- `aee_core_currentTurbulence`
- `aee_core_currentUVIndex`
- `aee_core_currentWBGT`
- `aee_core_currentWind`
- `aee_core_dustSuppression`
- `aee_core_dynamicLux`
- `aee_core_ehId_`
- `aee_core_enabled`
- `aee_core_fnc_calculateSeededWeatherProgression`
- `aee_core_geoAnchor`
- `aee_core_groundSurfaceTemp`
- `aee_core_hailActive`
- `aee_core_illuminanceLux`
- `aee_core_lightAzimuth`
- `aee_core_lightDirection`
- `aee_core_lightElevation`
- `aee_core_lightIsNight`
- `aee_core_logDebug`
- `aee_core_mgrsTables`
- `aee_core_moduleHealth`
- `aee_core_objectTemperatures`
- `aee_core_orographicFactor`
- `aee_core_overcast`
- `aee_core_positionDivergence`
- `aee_core_ppHandle_`
- `aee_core_ppHandle_optics_BaseGrade`
- `aee_core_precipitationPhase`
- `aee_core_realWeatherActive`
- `aee_core_simTime`
- `aee_core_snowDepth_m`
- `aee_core_snowfallRate`
- `aee_core_soilMoisture`
- `aee_core_starsVisibility`
- `aee_core_stormOverrideIntensity`
- `aee_core_stormOverrideType`
- `aee_core_stormOverrideUntil`
- `aee_core_updateInterval`
- `aee_core_windChillTemp`
- `aee_core_worldLocation`

### AEE-authored config classes

| Class | Declaring source |
|---|---|
| `AEE_Unknown_Other` | `addons/symbology/config.cpp` |
| `ColorAEE` | `addons/symbology/config.cpp` |
| `AEE_MarkerBase` | `addons/symbology/config.cpp` |
| `AEE_SandCloud` | `addons/particles/config.cpp` |
| `AEE_SnowCloud` | `addons/particles/config.cpp` |
| `AEE_SupersonicTrace` | `addons/particles/config.cpp` |
| `CfgClothing` | `addons/clothing/config.cpp` |

Engine classes AEE re-declares:

- `CfgWorlds` (`addons/lighting/config.cpp`)
- `CfgCloudlets` (`addons/particles/config.cpp`)
- `CfgMarkers` (`addons/symbology/config.cpp`)
- `CfgMarkerColors` (`addons/symbology/config.cpp`)
- `CfgMarkerClasses` (`addons/symbology/config.cpp`)

<!-- END GENERATED: extension contract -->

## Ceilings

- Config is load-time and global. The PBO is the only off switch (ADR-001).
- Between two mods that do not name each other, no deterministic order exists.
  An extension must declare `requiredAddons[] = {"aee_core"}` to load after AEE.
- The engine's C++ runtime (solver, renderer, flight model, ballistic
  integrator, AI routing) is not reachable by config or by script (ADR-017).
- A competitor's script namespace cannot be taken over without breaking it.
