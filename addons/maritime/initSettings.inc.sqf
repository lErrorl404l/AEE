// initSettings.inc.sqf - CBA Settings registration for aee_maritime
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// maritime stringtable.

// ── Tide ───────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(tideAmplitude,"AEE Maritime","Sea",0.5,5,2.0,1);

// ── Ocean current (issue #28) ──────────────────────────────────────────────
// The wind-driven and tidal surface current.  Channel depth and flood bearing
// are scenario parameters: the engine exposes no bathymetry or channel
// orientation, so the tidal current needs both to become a vector.
AEE_SETTING_CHECKBOX(oceanCurrentEnabled,"AEE Maritime","Current",true);
AEE_SETTING_SLIDER(oceanChannelDepth_m,"AEE Maritime","Current",5,200,30,0);
AEE_SETTING_SLIDER(oceanWindCurrentFraction,"AEE Maritime","Current",0.01,0.05,0.03,2);
AEE_SETTING_SLIDER(oceanDeflectionDeg,"AEE Maritime","Current",10,45,30,0);
AEE_SETTING_SLIDER(oceanTidalFloodBearing,"AEE Maritime","Current",0,360,0,0);

// ── Sea state ──────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(seaStateResponse,"AEE Maritime","Sea",0.1,0.9,0.3,2);

// ── Ship motion (issue #33) ────────────────────────────────────────────────
// Metacentric height GM drives the natural roll frequency
// (omega_n = sqrt(g*GM/k_xx^2)).  The engine publishes no hydrostatics, so
// GM is an operator input.  The 1.5 m default is a typical loaded
// metacentric height (bulk carrier 1.5-3.5 m, PNA Vol III).
AEE_SETTING_SLIDER(shipMetacentricHeight,"AEE Maritime","Sea",0.3,4,1.5,1);

// Roll, pitch and heave damping ratio zeta.  0.10 is the typical ship value
// quoted for roll; no primary source was pinned (ADR-043).
AEE_SETTING_SLIDER(shipDamping,"AEE Maritime","Sea",0.02,0.3,0.1,2);

// ── Sea-surface temperature (issue #37) ────────────────────────────────────
// Coupling weight between the air temperature and the latitude-seasonal
// climatology.  Low = high thermal inertia (sea stays near its climate
// baseline); high = the sea follows the air quickly.
AEE_SETTING_SLIDER(seaCouplingWeight,"AEE Maritime","Sea",0,1,0.5,2);

// ── Underwater light (issue #14) ───────────────────────────────────────────
// The water type is a Jerlov classification: 0 = I, 1 = IA, 2 = IB, 3 = II,
// 4 = III, 5 = 1, 6 = 3, 7 = 5, 8 = 7, 9 = 9.  It sets the diffuse
// attenuation of the three colour bands.  A world or biome layer can
// override it at run time through aee_maritime_waterType.
AEE_SETTING_CHECKBOX(underwaterLightEnabled,"AEE Maritime","Sea",true);
AEE_SETTING_SLIDER(underwaterWaterType,"AEE Maritime","Sea",0,9,3,0);
// ── Internal waves & thermocline (issue #17) ───────────────────────────────
// Two-layer internal-wave model.  The mixed layer is the thermocline depth;
// the deep layer is fixed at 1000 m.  The internal tide runs at the M2
// period (12.4206 h) with the configured amplitude.  See
// fnc_updateInternalWaves for the model and the sources.
AEE_SETTING_CHECKBOX(internalWaveEnabled,"AEE Maritime","Sea",true);
AEE_SETTING_SLIDER(thermoclineDepth,"AEE Maritime","Sea",10,200,50,0);
AEE_SETTING_SLIDER(thermoclineWidth,"AEE Maritime","Sea",10,100,30,0);
AEE_SETTING_SLIDER(internalTideAmplitude,"AEE Maritime","Sea",0,100,20,0);
// ── Underwater acoustics (issue #113) ──────────────────────────────────────
// The acoustics driver publishes the environmental sound state once per
// second.  The reference frequency sets the band for the published
// absorption and ambient noise; a scenario reads the sonar equation at its
// own frequency.  Salinity and the deep-water temperature set the sound
// speed profile; the thermocline depth is the shared Sea setting (issue #17).
AEE_SETTING_CHECKBOX(underwaterAcousticsEnabled,"AEE Maritime","Acoustics",true);
AEE_SETTING_SLIDER(acousticReferenceFreqHz,"AEE Maritime","Acoustics",50,20000,1000,0);
AEE_SETTING_SLIDER(seaSalinity,"AEE Maritime","Acoustics",30,40,35,1);
AEE_SETTING_SLIDER(deepWaterTemperature,"AEE Maritime","Acoustics",0,15,4,1);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_maritime_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Maritime",false);
