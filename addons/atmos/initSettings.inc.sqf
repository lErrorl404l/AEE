// initSettings.inc.sqf - CBA Settings registration for aee_atmos
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// atmos stringtable.

// ── Microburst ─────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(microburstTempThreshold,"AEE Atmos","Events",20,40,28,0);

AEE_SETTING_SLIDER(microburstChance,"AEE Atmos","Events",0,0.1,0.01,2);

AEE_SETTING_SLIDER(microburstDuration,"AEE Atmos","Events",5,60,12,0);

AEE_SETTING_SLIDER(microburstGustMax,"AEE Atmos","Events",20,50,36,0);

// ── Lightning ──────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(lightningConvectionTemp,"AEE Atmos","Events",20,35,25,0);

AEE_SETTING_SLIDER(lightningStrikeChance,"AEE Atmos","Events",0,0.2,0.05,2);

// ── Airframe icing ─────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(icingShedRate,"AEE Atmos","Icing",0.5,1,0.9,2);

AEE_SETTING_SLIDER(maxIceMass,"AEE Atmos","Icing",20,200,100,0);

// ── Fog ────────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(radFogRampRate,"AEE Atmos","Fog",0,0.5,0.1,2);

AEE_SETTING_SLIDER(maxFogDensity,"AEE Atmos","Fog",0.2,1,0.8,2);

// ── Refraction ────────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(refractionEnabled,"AEE Atmos","Refraction",true);

// ── Ice-crystal halos ──────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(haloEnabled,"AEE Atmos","Optics",true);

// ── Engine cloud quality ──────────────────────────────────────────────────
AEE_SETTING_SLIDER(simulWeatherLayers,"AEE Atmos","Clouds",0,5,0,0);

// ── Weather fronts ─────────────────────────────────────────────────────────
// Bergen life-cycle front (issue #15).  Off disables the whole front model:
// no temperature step, pressure trough, wind veer or cloud forcing.
AEE_SETTING_CHECKBOX(weatherFrontsEnabled,"AEE Atmos","Fronts",true);
// ── Volcanic ───────────────────────────────────────────────────────────────
// The eruption parameters.  The EDEN module overrides these per mission; the
// defaults describe a VEI 5 Plinian eruption.
AEE_SETTING_CHECKBOX(volcanicEnabled,"AEE Atmos","Volcanic",false);

AEE_SETTING_SLIDER(volcanicVEI,"AEE Atmos","Volcanic",0,8,5,0);

AEE_SETTING_SLIDER(volcanicVentAltitude,"AEE Atmos","Volcanic",0,6000,2000,0);

AEE_SETTING_SLIDER(volcanicAshEmission,"AEE Atmos","Volcanic",0,100000000,5000000,0);

AEE_SETTING_SLIDER(volcanicSO2Emission,"AEE Atmos","Volcanic",0,10000000,500000,0);

AEE_SETTING_SLIDER(volcanicHeatFlux,"AEE Atmos","Volcanic",0,1000000000000,100000000000,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_atmos_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Atmos",false);
