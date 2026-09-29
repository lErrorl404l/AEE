// initSettings.inc.sqf - CBA Settings registration for aee_environmental
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// environmental stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Frost ──────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FrostAccumRate,"AEE Environmental","Hydrology",0,0.01,0.001,3);

AEE_SETTING_SLIDER(FrostDecayRate,"AEE Environmental","Hydrology",0,0.05,0.01,2);

[
    QGVAR(groundFrostEnabled),
    "CHECKBOX",
    [LLSTRING(GroundFrostEnabled_Name), LLSTRING(GroundFrostEnabled_Description)],
    ["AEE Environmental", "Hydrology"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Snow ───────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(SnowAccretionRate,"AEE Environmental","Hydrology",0,0.1,0.01,2);

AEE_SETTING_SLIDER(MaxSnowDepth,"AEE Environmental","Hydrology",0.5,10,3.0,1);

// ── Severe Weather ─────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(SandstormWindThreshold,"AEE Environmental","Weather",5,25,10,0);

AEE_SETTING_SLIDER(BlowingSnowWindThreshold,"AEE Environmental","Weather",5,20,8,0);

AEE_SETTING_SLIDER(DustDevilTempThreshold,"AEE Environmental","Weather",25,40,30,0);

// ── Hydrology ──────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FlashFloodThreshold,"AEE Environmental","Weather",20,100,50,0);

AEE_SETTING_SLIDER(WettingRate,"AEE Environmental","Hydrology",0,0.2,0.05,2);

AEE_SETTING_SLIDER(DewRate,"AEE Environmental","Hydrology",0,0.1,0.02,2);

// ── Space Weather ──────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FlareChance,"AEE Environmental","Fire",0,0.2,0.05,2);

AEE_SETTING_SLIDER(FlareDuration,"AEE Environmental","Fire",600,36000,10800,0);

AEE_SETTING_SLIDER(FlareDecayRate,"AEE Environmental","Fire",0,0.2,0.05,2);

// ── Sound Propagation ──────────────────────────────────────────────────────
AEE_SETTING_SLIDER(InversionBoost,"AEE Environmental","Weather",0,1.5,0.6,1);

AEE_SETTING_SLIDER(SoundPropagationScale,"AEE Environmental","Sound",0.5,2,1.0,1);

// ── Avalanche slab model (#134) ────────────────────────────────────────────
// McClung & Schaerer shear-stress parameters.  Slab density and depth
// define tau = rho·g·h·sin(psi); the weak-layer strength is scaled from
// the snowpack quality.
AEE_SETTING_SLIDER(slabDensity,"AEE Environmental","Snow",100,400,300,0);

AEE_SETTING_SLIDER(slabDepth,"AEE Environmental","Snow",0.1,2,1.0,1);
