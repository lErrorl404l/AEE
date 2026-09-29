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

// ── Engine cloud quality ──────────────────────────────────────────────────
AEE_SETTING_SLIDER(simulWeatherLayers,"AEE Atmos","Clouds",0,5,0,0);
