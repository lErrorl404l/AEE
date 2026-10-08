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
        requiredAddons[] = {"aee_core", "aee_main"};
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
// addons/physiology/functions/clothing/fnc_getInventoryLoad.sqf
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
| `aee_armour` | `armour` |
| `aee_atmos` | `atmos` |
| `aee_ballistics` | `ballistics` |
| `aee_compat_ace3` | `compat_ace3` |
| `aee_compat_acm` | `compat_acm` |
| `aee_compat_acre2` | `compat_acre2` |
| `aee_compat_kat` | `compat_kat` |
| `aee_compat_realweather` | `compat_realweather` |
| `aee_compat_tfar` | `compat_tfar` |
| `aee_core` | `core` |
| `aee_environmental` | `environmental` |
| `aee_fx` | `fx` |
| `aee_main` | `main` |
| `aee_maritime` | `maritime` |
| `aee_material` | `material` |
| `aee_mobility` | `mobility` |
| `aee_nightvision` | `nightvision` |
| `aee_optics` | `optics` |
| `aee_physiology` | `physiology` |
| `aee_radio` | `radio` |
| `aee_thermal` | `thermal` |
| `aee_wildlife` | `wildlife` |

### Public functions (631)

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
- `aee_armour_fnc_deriveProtection`
- `aee_armour_fnc_dumpState`
- `aee_armour_fnc_getVehicleArmour`
- `aee_armour_fnc_penetrationGate`
- `aee_atmos_fnc_calculateAirframeIcing`
- `aee_atmos_fnc_calculateCloudCeiling`
- `aee_atmos_fnc_calculateCloudDevelopment`
- `aee_atmos_fnc_calculateHailEnergy`
- `aee_atmos_fnc_calculateHaze`
- `aee_atmos_fnc_calculateLightning`
- `aee_atmos_fnc_calculateMicroburst`
- `aee_atmos_fnc_calculateOrographicPrecipitation`
- `aee_atmos_fnc_calculatePrecipitationPhase`
- `aee_atmos_fnc_calculatePressureTrend`
- `aee_atmos_fnc_calculateRefraction`
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
- `aee_core_fnc_attachObjectEngineHandler`
- `aee_core_fnc_buildGeoAnchor`
- `aee_core_fnc_calculateIlluminance`
- `aee_core_fnc_calculateSeededWeatherProgression`
- `aee_core_fnc_consistencyFailureLine`
- `aee_core_fnc_consistencyLoadTable`
- `aee_core_fnc_consistencyLog`
- `aee_core_fnc_coreBodyTemp`
- `aee_core_fnc_createPPEffect`
- `aee_core_fnc_datalinkState`
- `aee_core_fnc_destroyPPEffect`
- `aee_core_fnc_deterministicRandom`
- `aee_core_fnc_diagnostic`
- `aee_core_fnc_dumpPerformanceCounters`
- `aee_core_fnc_dumpState`
- `aee_core_fnc_evaluateConsistency`
- `aee_core_fnc_evaluateGeoConsistency`
- `aee_core_fnc_formatMgrs`
- `aee_core_fnc_getEyeState`
- `aee_core_fnc_getGeoAnchor`
- `aee_core_fnc_getSmoothedWeather`
- `aee_core_fnc_getWorldLocation`
- `aee_core_fnc_gnssErrorEllipse`
- `aee_core_fnc_gnssFixState`
- `aee_core_fnc_handleCollisionDamage`
- `aee_core_fnc_init`
- `aee_core_fnc_installObjectEngineHandler`
- `aee_core_fnc_installPlayerEngineHandler`
- `aee_core_fnc_latLonToUtm`
- `aee_core_fnc_mgrsToWorld`
- `aee_core_fnc_moduleInit`
- `aee_core_fnc_moduleStormInit`
- `aee_core_fnc_parseMgrs`
- `aee_core_fnc_readState`
- `aee_core_fnc_reportModuleHealth`
- `aee_core_fnc_runConsistencyCheck`
- `aee_core_fnc_runGeoConsistency`
- `aee_core_fnc_updateEnvironment`
- `aee_core_fnc_utmToLatLon`
- `aee_core_fnc_utmToWorld`
- `aee_core_fnc_worldToMgrs`
- `aee_environmental_fnc_applyWorldLighting`
- `aee_environmental_fnc_calculateAvalancheRisk`
- `aee_environmental_fnc_calculateBiologicalAmbient`
- `aee_environmental_fnc_calculateBlowingSnowVisibility`
- `aee_environmental_fnc_calculateCBRNPersistence`
- `aee_environmental_fnc_calculateConcealment`
- `aee_environmental_fnc_calculateCropState`
- `aee_environmental_fnc_calculateDustSuppression`
- `aee_environmental_fnc_calculateDustVisibility`
- `aee_environmental_fnc_calculateFireSpreadRisk`
- `aee_environmental_fnc_calculateFlashFloodRisk`
- `aee_environmental_fnc_calculateFogBaseAltitude`
- `aee_environmental_fnc_calculateFreezeThawCycling`
- `aee_environmental_fnc_calculateFrostOnWindscreens`
- `aee_environmental_fnc_calculateIceLoad`
- `aee_environmental_fnc_calculateLimitingMagnitude`
- `aee_environmental_fnc_calculateLunarIllumination`
- `aee_environmental_fnc_calculateMicroclimate`
- `aee_environmental_fnc_calculateQNH`
- `aee_environmental_fnc_calculateScentDispersion`
- `aee_environmental_fnc_calculateSevereWeather`
- `aee_environmental_fnc_calculateSnowAccumulation`
- `aee_environmental_fnc_calculateSolarRadiation`
- `aee_environmental_fnc_calculateSpaceWeather`
- `aee_environmental_fnc_calculateSurfaceWetness`
- `aee_environmental_fnc_calculateUrbanHeatIsland`
- `aee_environmental_fnc_calculateWaterInfluence`
- `aee_environmental_fnc_classifyBiome`
- `aee_environmental_fnc_classifyNight`
- `aee_environmental_fnc_detectGroundFrost`
- `aee_environmental_fnc_drawFaintStars`
- `aee_environmental_fnc_drawMilkyWay`
- `aee_environmental_fnc_galacticToEquatorial`
- `aee_environmental_fnc_galacticToHorizontal`
- `aee_environmental_fnc_getBiome`
- `aee_environmental_fnc_getBiomeAtPosition`
- `aee_environmental_fnc_getBiomeName`
- `aee_environmental_fnc_getCbrnProtection`
- `aee_environmental_fnc_getClimateNormals`
- `aee_environmental_fnc_getCoastDistance`
- `aee_environmental_fnc_getLatitudeClimate`
- `aee_environmental_fnc_getSmoothedBiome`
- `aee_environmental_fnc_getStarCatalog`
- `aee_environmental_fnc_lightPollutionPenalty`
- `aee_environmental_fnc_logSkyState`
- `aee_environmental_fnc_meteorRate`
- `aee_environmental_fnc_meteorShowers`
- `aee_environmental_fnc_meteorState`
- `aee_environmental_fnc_radiantHorizontal`
- `aee_environmental_fnc_renderAurora`
- `aee_environmental_fnc_renderDynamicStars`
- `aee_environmental_fnc_renderMeteors`
- `aee_environmental_fnc_renderMilkyWay`
- `aee_environmental_fnc_scanTerrainSignals`
- `aee_environmental_fnc_showerIsActive`
- `aee_environmental_fnc_siderealTime`
- `aee_environmental_fnc_skyGateReason`
- `aee_environmental_fnc_starBrightnessCoefficient`
- `aee_environmental_fnc_starCatalogData`
- `aee_environmental_fnc_starDirection`
- `aee_environmental_fnc_starLightsSync`
- `aee_environmental_fnc_starMagnitude`
- `aee_environmental_fnc_starWeatherFade`
- `aee_environmental_fnc_updateAurora`
- `aee_environmental_fnc_updateBiomePosition`
- `aee_environmental_fnc_updateMeteors`
- `aee_environmental_fnc_updateMilkyWay`
- `aee_environmental_fnc_updateSeasonalFoliage`
- `aee_environmental_fnc_updateSoilMoisture`
- `aee_environmental_fnc_updateSoundPropagation`
- `aee_environmental_fnc_worldLightingClass`
- `aee_environmental_fnc_worldLightingProfile`
- `aee_fx_fnc_applyAtmosphericDust`
- `aee_fx_fnc_applyBreathCondensation`
- `aee_fx_fnc_applyExhaustShimmer`
- `aee_fx_fnc_applyFootfallDust`
- `aee_fx_fnc_applyRainSurfaceDrops`
- `aee_fx_fnc_applyRainVehicleSound`
- `aee_fx_fnc_applyRotorWash`
- `aee_fx_fnc_applyVehicleDust`
- `aee_fx_fnc_applyWeatherParticles`
- `aee_fx_fnc_applyWindNoise`
- `aee_fx_fnc_calculateBlastInjury`
- `aee_fx_fnc_calculateBlastOverpressure`
- `aee_fx_fnc_calculateDownwash`
- `aee_fx_fnc_calculateLightningStrikeEffects`
- `aee_fx_fnc_dumpState`
- `aee_fx_fnc_heatHazeAlpha`
- `aee_fx_fnc_heatHazeSize`
- `aee_fx_fnc_kickupParams`
- `aee_fx_fnc_particleAllocate`
- `aee_fx_fnc_particleEffectConfig`
- `aee_fx_fnc_particleEmission`
- `aee_fx_fnc_particleMaterial`
- `aee_fx_fnc_particlePipeline`
- `aee_fx_fnc_particlePipelineEmit`
- `aee_fx_fnc_particleState`
- `aee_fx_fnc_registerParticleSource`
- `aee_fx_fnc_renderSupersonicTrace`
- `aee_fx_fnc_surfaceMaterial`
- `aee_fx_fnc_surfaceSample`
- `aee_fx_fnc_triggerLightning`
- `aee_fx_fnc_triggerSevereWeatherFX`
- `aee_fx_fnc_weatherParticleAlpha`
- `aee_maritime_fnc_calculateCompassDeviation`
- `aee_maritime_fnc_calculateMagneticAnomaly`
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
- `aee_mobility_fnc_applyAirframeLoad`
- `aee_mobility_fnc_applyFlightTurbulence`
- `aee_mobility_fnc_applyGripLoss`
- `aee_mobility_fnc_applyRollover`
- `aee_mobility_fnc_applyTerrainDrag`
- `aee_mobility_fnc_calculateAccretionMass`
- `aee_mobility_fnc_calculateAeroPenalty`
- `aee_mobility_fnc_calculateAirEngineLoad`
- `aee_mobility_fnc_calculateBaseflow`
- `aee_mobility_fnc_calculateDepressionStorage`
- `aee_mobility_fnc_calculateEngineLoad`
- `aee_mobility_fnc_calculateEnginePower`
- `aee_mobility_fnc_calculateExhaustPlume`
- `aee_mobility_fnc_calculateGreenAmptInfiltration`
- `aee_mobility_fnc_calculateHelicopterLift`
- `aee_mobility_fnc_calculateMudAccretion`
- `aee_mobility_fnc_calculateRiverWaterLevel`
- `aee_mobility_fnc_calculateRolloverThreshold`
- `aee_mobility_fnc_calculateRouteDegradation`
- `aee_mobility_fnc_calculateRunoffSCS`
- `aee_mobility_fnc_calculateSSF`
- `aee_mobility_fnc_calculateSoilBearingStrength`
- `aee_mobility_fnc_calculateSoilStrength`
- `aee_mobility_fnc_calculateTerrainLimits`
- `aee_mobility_fnc_calculateThermalRefraction`
- `aee_mobility_fnc_calculateTraction`
- `aee_mobility_fnc_calculateTurbulenceForce`
- `aee_mobility_fnc_calculateWetTraction`
- `aee_mobility_fnc_classifyVehicle`
- `aee_mobility_fnc_estimateVehicleMass`
- `aee_mobility_fnc_estimateVehicleMassCore`
- `aee_mobility_fnc_getAircraftData`
- `aee_mobility_fnc_getAircraftMatch`
- `aee_mobility_fnc_getNearbyVehicles`
- `aee_mobility_fnc_getTerrainSpeedFactor`
- `aee_mobility_fnc_getVehicleBands`
- `aee_mobility_fnc_getVehicleData`
- `aee_mobility_fnc_getVehicleGeometry`
- `aee_mobility_fnc_getVehicleMassModel`
- `aee_mobility_fnc_getVehicleMatch`
- `aee_mobility_fnc_logAirframeState`
- `aee_mobility_fnc_resolveFlightModel`
- `aee_mobility_fnc_routeRunoffD8`
- `aee_mobility_fnc_updateGroundState`
- `aee_nightvision_fnc_applyNVGTubeModel`
- `aee_nightvision_fnc_applyNightGrain`
- `aee_nightvision_fnc_dumpState`
- `aee_nightvision_fnc_getDeviceData`
- `aee_nightvision_fnc_getDeviceMatch`
- `aee_nightvision_fnc_getNvgDeviceProperties`
- `aee_nightvision_fnc_getNvgTubeModel`
- `aee_nightvision_fnc_ltmBeamSegments`
- `aee_nightvision_fnc_ltmCreate`
- `aee_nightvision_fnc_ltmDaylightAlpha`
- `aee_nightvision_fnc_ltmDraw`
- `aee_nightvision_fnc_ltmInit`
- `aee_nightvision_fnc_ltmPFH`
- `aee_nightvision_fnc_ltmToggle`
- `aee_nightvision_fnc_ltmToggleMode`
- `aee_nightvision_fnc_nvgAgcBreathing`
- `aee_nightvision_fnc_nvgBlemishField`
- `aee_nightvision_fnc_nvgBlindingEnvelope`
- `aee_nightvision_fnc_nvgPincushion`
- `aee_nightvision_fnc_nvgScintillation`
- `aee_nightvision_fnc_nvgTierIndex`
- `aee_nightvision_fnc_teardownNvgDoF`
- `aee_optics_fnc_applyAtmosphericSeeingFX`
- `aee_optics_fnc_applyBaseGrade`
- `aee_optics_fnc_applyDewOnOpticsFX`
- `aee_optics_fnc_applyHeatShimmerFX`
- `aee_optics_fnc_applyMirageFX`
- `aee_optics_fnc_applyRainOnOpticsFX`
- `aee_optics_fnc_applySnowBlindnessFX`
- `aee_optics_fnc_applySolarGlareFX`
- `aee_optics_fnc_applyWeatherGrain`
- `aee_optics_fnc_baseGradeParams`
- `aee_optics_fnc_calculateAtmosphericSeeing`
- `aee_optics_fnc_calculateAttenuation`
- `aee_optics_fnc_calculateDewOnOptics`
- `aee_optics_fnc_calculateMirageIntensity`
- `aee_optics_fnc_calculatePrecipitationVisibility`
- `aee_optics_fnc_calculateRainOnOptics`
- `aee_optics_fnc_calculateSmokePersistence`
- `aee_optics_fnc_calculateSnowBlindness`
- `aee_optics_fnc_calculateSolarGlare`
- `aee_optics_fnc_calculateVehicleHeatShimmer`
- `aee_optics_fnc_calculateViewDistance`
- `aee_optics_fnc_destroyBasePostProcess`
- `aee_optics_fnc_dtvHostStart`
- `aee_optics_fnc_dtvHostStop`
- `aee_optics_fnc_dtvHostTick`
- `aee_optics_fnc_dumpState`
- `aee_optics_fnc_enterThermalSensors`
- `aee_optics_fnc_exitThermalSensors`
- `aee_optics_fnc_eyeAdaptInit`
- `aee_optics_fnc_eyeAdaptState`
- `aee_optics_fnc_eyeAdaptStep`
- `aee_optics_fnc_eyeAmbientLux`
- `aee_optics_fnc_eyeAperture`
- `aee_optics_fnc_eyeFlash`
- `aee_optics_fnc_eyeLimits`
- `aee_optics_fnc_eyeLocalLux`
- `aee_optics_fnc_eyeMesopicWeight`
- `aee_optics_fnc_eyePupilSteady`
- `aee_optics_fnc_eyePupilStep`
- `aee_optics_fnc_eyeSampleScene`
- `aee_optics_fnc_eyeSceneLux`
- `aee_optics_fnc_eyeSkyCast`
- `aee_optics_fnc_eyeSkyFraction`
- `aee_optics_fnc_fontFamilyUsable`
- `aee_optics_fnc_formatGridDisplay`
- `aee_optics_fnc_getOpticProperties`
- `aee_optics_fnc_gpsBuild`
- `aee_optics_fnc_gpsUpdate`
- `aee_optics_fnc_hudBuild`
- `aee_optics_fnc_hudFormatGrid`
- `aee_optics_fnc_hudFormatHeading`
- `aee_optics_fnc_hudFormatRange`
- `aee_optics_fnc_hudMarkers`
- `aee_optics_fnc_hudRangefinder`
- `aee_optics_fnc_hudUpdate`
- `aee_optics_fnc_initBaseGrade`
- `aee_optics_fnc_initEyeAdaptation`
- `aee_optics_fnc_initWeatherGrain`
- `aee_optics_fnc_managePostProcess`
- `aee_optics_fnc_mgrsCursorText`
- `aee_optics_fnc_mgrsEffectivePrecision`
- `aee_optics_fnc_mgrsFontFamily`
- `aee_optics_fnc_mgrsGridLines`
- `aee_optics_fnc_mgrsMapDraw`
- `aee_optics_fnc_mgrsMapPrecision`
- `aee_optics_fnc_mgrsMarkerText`
- `aee_optics_fnc_perceptionAdaptState`
- `aee_optics_fnc_perceptionBaseGrade`
- `aee_optics_fnc_perceptionChromaticAdaptation`
- `aee_optics_fnc_perceptionDetectDeviation`
- `aee_optics_fnc_perceptionIlluminant`
- `aee_optics_fnc_perceptionMesopicColor`
- `aee_optics_fnc_perceptionParams`
- `aee_optics_fnc_perceptionSample`
- `aee_optics_fnc_perceptionToneResponse`
- `aee_optics_fnc_perceptionUpdate`
- `aee_optics_fnc_ppEffectCreate`
- `aee_optics_fnc_runThermalPass`
- `aee_optics_fnc_shadowClassifyScene`
- `aee_optics_fnc_shadowFpsGovernor`
- `aee_optics_fnc_shadowSamplePattern`
- `aee_optics_fnc_shadowSmoothDistance`
- `aee_optics_fnc_shadowStabilizeDepth`
- `aee_optics_fnc_shadowTargetDistance`
- `aee_optics_fnc_symbolCategory`
- `aee_optics_fnc_symbolFrame`
- `aee_optics_fnc_symbolIcon`
- `aee_optics_fnc_symbolPalette`
- `aee_optics_fnc_symbolResolve`
- `aee_optics_fnc_symbologyAffiliation`
- `aee_optics_fnc_symbologyDimension`
- `aee_optics_fnc_symbologyEchelon`
- `aee_optics_fnc_symbologyEchelonMarker`
- `aee_optics_fnc_symbologyMarkerCategory`
- `aee_optics_fnc_symbologyMarkerColor`
- `aee_optics_fnc_symbologyMarkerType`
- `aee_optics_fnc_symbologyMarkers`
- `aee_optics_fnc_symbologyMarkersApply`
- `aee_optics_fnc_symbologyMarkersRestore`
- `aee_optics_fnc_symbologyPaletteFriendly`
- `aee_optics_fnc_symbologyUnitCategory`
- `aee_optics_fnc_symbologyUnitDimension`
- `aee_optics_fnc_symbologyUnitEchelon`
- `aee_optics_fnc_symbologyWorldDraw`
- `aee_optics_fnc_teardownBaseGrade`
- `aee_optics_fnc_teardownSensors`
- `aee_optics_fnc_trackerDraw`
- `aee_optics_fnc_trackerProject`
- `aee_optics_fnc_trackerUpdate`
- `aee_optics_fnc_updateEyeAdaptation`
- `aee_optics_fnc_updateThermalHost`
- `aee_optics_fnc_updateThermalHostSetting`
- `aee_optics_fnc_weatherGrainParams`
- `aee_physiology_fnc_applyCrossSensitivity`
- `aee_physiology_fnc_applyHeatStressHUD`
- `aee_physiology_fnc_applyMovementSpeed`
- `aee_physiology_fnc_calculateAltitudeAcclimatization`
- `aee_physiology_fnc_calculateAltitudeDCS`
- `aee_physiology_fnc_calculateBarometricPressure`
- `aee_physiology_fnc_calculateColdWeatherPerformance`
- `aee_physiology_fnc_calculateDehydrationRisk`
- `aee_physiology_fnc_calculateFatigueFactor`
- `aee_physiology_fnc_calculateGLOC`
- `aee_physiology_fnc_calculateHypoxia`
- `aee_physiology_fnc_calculateOxygenDelivery`
- `aee_physiology_fnc_calculateShooterStability`
- `aee_physiology_fnc_calculateSleepPressure`
- `aee_physiology_fnc_calculateUVIndex`
- `aee_physiology_fnc_dumpState`
- `aee_physiology_fnc_getCamouflageProperties`
- `aee_physiology_fnc_getDiveState`
- `aee_physiology_fnc_getEquipmentBands`
- `aee_physiology_fnc_getEquipmentProperties`
- `aee_physiology_fnc_getGLoad`
- `aee_physiology_fnc_getGloveProperties`
- `aee_physiology_fnc_getGoggleProperties`
- `aee_physiology_fnc_getHelmetProperties`
- `aee_physiology_fnc_getInventoryLoad`
- `aee_physiology_fnc_getItemMass`
- `aee_physiology_fnc_getMagazineLoad`
- `aee_physiology_fnc_getMagazineMass`
- `aee_physiology_fnc_getNirPerSelection`
- `aee_physiology_fnc_getNvgContrast`
- `aee_physiology_fnc_getPackProperties`
- `aee_physiology_fnc_getUniformProperties`
- `aee_physiology_fnc_getVestProperties`
- `aee_physiology_fnc_getWeaponLoad`
- `aee_physiology_fnc_getWeaponMass`
- `aee_physiology_fnc_integrateSwayFactor`
- `aee_physiology_fnc_selectBand`
- `aee_physiology_fnc_updateDiveState`
- `aee_physiology_fnc_updateFatigueState`
- `aee_physiology_fnc_zh16cStep`
- `aee_radio_fnc_calculateIonosphericAbsorption`
- `aee_radio_fnc_calculateRadioPropagation`
- `aee_radio_fnc_dumpState`
- `aee_thermal_fnc_activeIRGate`
- `aee_thermal_fnc_addGroundStamp`
- `aee_thermal_fnc_applyActiveIR`
- `aee_thermal_fnc_applyBuildingThermal`
- `aee_thermal_fnc_applyClothingThermal`
- `aee_thermal_fnc_applyContactConduction`
- `aee_thermal_fnc_applyEngineThermal`
- `aee_thermal_fnc_applyExhaustHeat`
- `aee_thermal_fnc_applyFusionFill`
- `aee_thermal_fnc_applyFusionOverlay`
- `aee_thermal_fnc_applyFusionPP`
- `aee_thermal_fnc_applyFusionSun`
- `aee_thermal_fnc_applyGroundContactStamps`
- `aee_thermal_fnc_applyImpactHeat`
- `aee_thermal_fnc_applyRadiativeExchange`
- `aee_thermal_fnc_applyRainDroplets`
- `aee_thermal_fnc_applySecondSun`
- `aee_thermal_fnc_applySelectionThermal`
- `aee_thermal_fnc_applyThermalVision`
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
- `aee_thermal_fnc_cycleFusionMode`
- `aee_thermal_fnc_dumpState`
- `aee_thermal_fnc_evaluateThermalEdge`
- `aee_thermal_fnc_expandThermalSelectionTree`
- `aee_thermal_fnc_fusionBandIndex`
- `aee_thermal_fnc_fusionFovGate`
- `aee_thermal_fnc_fusionFrameGeometry`
- `aee_thermal_fnc_fusionFrameVisible`
- `aee_thermal_fnc_fusionGateDecision`
- `aee_thermal_fnc_fusionMaterialPaths`
- `aee_thermal_fnc_fusionThermalField`
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
- `aee_thermal_fnc_hudBoxDraw`
- `aee_thermal_fnc_hudTapeActive`
- `aee_thermal_fnc_hudTapeBoot`
- `aee_thermal_fnc_hudTapeBuild`
- `aee_thermal_fnc_hudTapeDraw`
- `aee_thermal_fnc_hudTapeInfo`
- `aee_thermal_fnc_isFusionCapable`
- `aee_thermal_fnc_isPositionShadowed`
- `aee_thermal_fnc_isThermalHostActive`
- `aee_thermal_fnc_outlineCanvas`
- `aee_thermal_fnc_outlineCollect`
- `aee_thermal_fnc_outlineDraw`
- `aee_thermal_fnc_outlineGearRadius`
- `aee_thermal_fnc_outlineSensorLod`
- `aee_thermal_fnc_outlineSkeleton`
- `aee_thermal_fnc_outlineToggle`
- `aee_thermal_fnc_outlineTopo`
- `aee_thermal_fnc_planckBandRadiance`
- `aee_thermal_fnc_probeThermalCapability`
- `aee_thermal_fnc_resolveFusionDevice`
- `aee_thermal_fnc_resolvePaintIndexFromSelections`
- `aee_thermal_fnc_resolveSelectionPaintIndex`
- `aee_thermal_fnc_resolveThermalBand`
- `aee_thermal_fnc_resolveThermalTarget`
- `aee_thermal_fnc_resolveThermalVisibility`
- `aee_thermal_fnc_solarElevation`
- `aee_thermal_fnc_solveTwoNodeSelection`
- `aee_thermal_fnc_startActiveIR`
- `aee_thermal_fnc_stopActiveIR`
- `aee_thermal_fnc_takeThermalSweep`
- `aee_thermal_fnc_thermalImperfectionParams`
- `aee_thermal_fnc_thermalPalette`
- `aee_thermal_fnc_thermalResolutionParams`
- `aee_thermal_fnc_thermalWetDistortionParams`
- `aee_thermal_fnc_updateFusionFrame`
- `aee_thermal_fnc_updateTemperature`
- `aee_thermal_fnc_updateThermalAGC`
- `aee_wildlife_fnc_acousticLevel`
- `aee_wildlife_fnc_acousticOccluders`
- `aee_wildlife_fnc_acousticPublish`
- `aee_wildlife_fnc_acousticSample`
- `aee_wildlife_fnc_acousticSourceDb`
- `aee_wildlife_fnc_applyAnimalBehaviour`
- `aee_wildlife_fnc_callEmit`
- `aee_wildlife_fnc_callPitch`
- `aee_wildlife_fnc_callPublish`
- `aee_wildlife_fnc_callReceive`
- `aee_wildlife_fnc_callSample`
- `aee_wildlife_fnc_cullFauna`
- `aee_wildlife_fnc_disturbanceSilence`
- `aee_wildlife_fnc_ecologyBudget`
- `aee_wildlife_fnc_ecologyTick`
- `aee_wildlife_fnc_emitterClass`
- `aee_wildlife_fnc_emitterPlan`
- `aee_wildlife_fnc_emitterRelease`
- `aee_wildlife_fnc_emitterSync`
- `aee_wildlife_fnc_environmentGrid`
- `aee_wildlife_fnc_environmentSuitability`
- `aee_wildlife_fnc_getCallPattern`
- `aee_wildlife_fnc_getSeason`
- `aee_wildlife_fnc_getSpeciesMatch`
- `aee_wildlife_fnc_habitatBoundary`
- `aee_wildlife_fnc_initWildlife`
- `aee_wildlife_fnc_logWildlifeState`
- `aee_wildlife_fnc_monitorWildlife`
- `aee_wildlife_fnc_needsTick`
- `aee_wildlife_fnc_pickBedSource`
- `aee_wildlife_fnc_pickResourceTarget`
- `aee_wildlife_fnc_playAmbientBed`
- `aee_wildlife_fnc_playOneShot`
- `aee_wildlife_fnc_resourceScore`
- `aee_wildlife_fnc_sampleNeighbourhood`
- `aee_wildlife_fnc_shotAudio`
- `aee_wildlife_fnc_soundBedForContext`
- `aee_wildlife_fnc_soundTick`
- `aee_wildlife_fnc_spawnBudget`
- `aee_wildlife_fnc_spawnFauna`
- `aee_wildlife_fnc_speciesDeprecation`
- `aee_wildlife_fnc_speciesForBiome`
- `aee_wildlife_fnc_speciesSound`
- `aee_wildlife_fnc_spookRange`
- `aee_wildlife_fnc_spookWave`
- `aee_wildlife_fnc_teardownWildlife`
- `aee_wildlife_fnc_vegScore`
- `aee_wildlife_fnc_wildlifePerceive`
- `aee_wildlife_fnc_wildlifeThink`
- `aee_wildlife_fnc_wildlifeTick`
- `aee_wildlife_fnc_wildlifeTickPFH`

### Public core state variables (73)

The `aee_core_*` mission variables. The canonical list of every published variable is `docs/wiki/chapters/state-variables.qmd`; these are the names that appear in the source as a contract surface.

- `aee_core_ambientLux`
- `aee_core_avgGroundTemp`
- `aee_core_biome`
- `aee_core_camoCoefficient`
- `aee_core_cbrnPersistence`
- `aee_core_clothingInsulation`
- `aee_core_consistencyFailures`
- `aee_core_consistencyState`
- `aee_core_consistencyStrict`
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
- `aee_core_fnc_buildGeoAnchor`
- `aee_core_fnc_calculateSeededWeatherProgression`
- `aee_core_fnc_datalinkState`
- `aee_core_fnc_dumpState`
- `aee_core_fnc_evaluateGeoConsistency`
- `aee_core_fnc_formatMgrs`
- `aee_core_fnc_getGeoAnchor`
- `aee_core_fnc_gnssErrorEllipse`
- `aee_core_fnc_gnssFixState`
- `aee_core_fnc_latLonToUtm`
- `aee_core_fnc_mgrsToWorld`
- `aee_core_fnc_parseMgrs`
- `aee_core_fnc_reportModuleHealth`
- `aee_core_fnc_runConsistencyCheck`
- `aee_core_fnc_runGeoConsistency`
- `aee_core_fnc_utmToLatLon`
- `aee_core_fnc_utmToWorld`
- `aee_core_fnc_worldToMgrs`
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
| `AEE_Symbology` | `addons/optics/config.cpp` |
| `ColorAEE` | `addons/optics/config.cpp` |
| `AEE_MarkerBase` | `addons/optics/config.cpp` |
| `AEE_SandCloud` | `addons/core/config.cpp` |
| `AEE_SnowCloud` | `addons/core/config.cpp` |
| `AEE_SupersonicTrace` | `addons/fx/config.cpp` |
| `CfgClothing` | `addons/physiology/config.cpp` |

Engine classes AEE re-declares:

- `CfgWorlds` (`addons/environmental/config.cpp`)
- `CfgCloudlets` (`addons/core/config.cpp`)
- `CfgMarkers` (`addons/optics/config.cpp`)
- `CfgMarkerColors` (`addons/optics/config.cpp`)
- `CfgMarkerClasses` (`addons/optics/config.cpp`)

<!-- END GENERATED: extension contract -->

## Ceilings

- Config is load-time and global. The PBO is the only off switch (ADR-001).
- Between two mods that do not name each other, no deterministic order exists.
  An extension must declare `requiredAddons[] = {"aee_core"}` to load after AEE.
- The engine's C++ runtime (solver, renderer, flight model, ballistic
  integrator, AI routing) is not reachable by config or by script (ADR-017).
- A competitor's script namespace cannot be taken over without breaking it.
