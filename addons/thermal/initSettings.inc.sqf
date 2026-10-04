// ── Thermal polarity (issue #196) ─────────────────────────────────────────
// White-hot (0) is the system default - the AN/PAS-13 initialises white
// hot.  Black-hot (1) is a user-selectable alternative; FM 3-22.9
// Appendix H states polarity choice is user preference, not doctrine.
// Lives here (aee_thermal) with the rest of the thermal pipeline - the
// optics module owns NVG/normal vision only.
[
    QGVAR(thermalPolarity),
    "LIST",
    [LLSTRING(thermalPolarity_Name), LLSTRING(thermalPolarity_Description)],
    ["AEE Thermal", "Display"],
    [[0, 1], ["White hot", "Black hot"], 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fusion (issue #204, Track B ENVG-B) ───────────────────────────────────
// Off: fusion only on TI-capable headsets (visionMode includes "TI").
// On:  fusion renders over ANY NVG, thermal source or not (the A3TI
// approach - its fusion modes are offered whenever an optic has thermal
// and the current vanilla mode is NVG).  Capability is not consent: this
// setting only grants the option, the operator still presses the keybind.
AEE_SETTING_CHECKBOX(fusionAlwaysOn,"AEE Experimental","Fusion",false);

// The fusion FOV frame (issue #204).  A thin rectangular HUD border at the
// thermal channel's resolved half-angle, so the operator can see where the
// fused image is actually bounded.  Default ON.  It is an operator aid and
// not optics: no mask and no tube geometry, and it draws nothing for a
// non-fusion device.
AEE_SETTING_CHECKBOX(fusionFovFrame,"AEE Experimental","Fusion",true);

// The fusion thermal-outline overlay (issue #204).  Outlines the hot targets
// the thermal state already tracks, so the operator sees which bodies the
// fused channel resolves.  It draws nothing when fusion is off, because the
// NVG dispatch calls the toggle only on the fusion path.
AEE_SETTING_CHECKBOX(fusionOutline,"AEE Experimental","Fusion",true);

// The fusion solid fill (issue #204).  Ported from workshop 3810296503
// whale_ecoti_llll functions/fn_thermalFill.sqf.  On: a hot body inside the
// thermal channel has every texture slot painted one solid bright colour, so
// the engine renders it as the flat block a real thermal display shows.  It
// REPLACES the 256-band emissive ladder while it is on, so one body is never
// painted by both primitives.  Default OFF: the graded ladder stays the
// default look.
AEE_SETTING_CHECKBOX(fusionSolidFill,"AEE Experimental","Fusion",false);

// The drawn fusion display (issue #204).  Ported from workshop 3810296503
// whale_ecoti_llll RscTitles \ whale_ecoti_llll_overlay: a tinted glass panel
// over the NVG image plus a scrolling compass tape with the grid, height, time
// and the aee environment state.  This is the PRIMARY fusion readout.  The
// aee_optics environment HUD (AEE Optics > Display > Environment HUD) is the
// auxiliary panel; it is a separate display with separate controls, so no
// control is drawn twice, but it repeats the environment state, so enable one
// or the other to avoid a duplicated readout.  Default ON.
AEE_SETTING_CHECKBOX(fusionHud,"AEE HUD","Displays",true);

// ── Fixed-pattern noise (issue #204, FPN) ────────────────────────────────
// Real LWIR sensors show a static spatial mottle (fixed-pattern noise)
// over the thermal image, independent of the temporal FilmGrain.  On:
// painted thermal objects get the ti_fpn.rvmat material (perlinNoise
// Stage2 multiplying the painted heat colour).  The material swap is
// client-local and restored on thermal EXIT.
AEE_SETTING_CHECKBOX(thermalFPN,"AEE Thermal","Display",true);
// Runtime kill switch for the thermal post-process chain.  The five effects are
// FULL-SCREEN render passes (two of them blurs), and they are the only engine
// render work AEE adds in thermal beyond the engine's own thermal pass.  Turning
// this off isolates that cost in-game, with no rebuild.  Default on.
AEE_SETTING_CHECKBOX(thermalPPEffects,"AEE Thermal","Display",true);

// ── Base channel (issue #196 prototype) ───────────────────────────────────
// The engine renders thermal on its own TI channel (vision mode 2).  The
// proven A3TI/MKK route instead disables the vehicle's native TI and draws
// the thermal display over the day (DTV) channel, so the engine's TI pass
// cannot fight the mod's.  This setting selects the host channel.  Vanilla
// TI is the default: nothing changes until DTV is chosen.  DTV is
// vehicle-only (the player must be in an optic).
[
    QGVAR(thermalBaseChannel),
    "LIST",
    [LLSTRING(thermalBaseChannel_Name), LLSTRING(thermalBaseChannel_Description)],
    ["AEE Thermal", "Display"],
    [[0, 1], ["Vanilla TI", "DTV"], 0],
    true,
    {
        [] call EFUNC(optics,updateThermalHostSetting);
    }
] call CBA_fnc_addSetting;

// ── Thermal diagnostics (issue #203, standalone decoupling) ─────────────
// Thermal's own debug flag - previously borrowed nightvision's nvgDebug,
// a cross-module coupling that blocked thermal as a standalone addon.
AEE_SETTING_CHECKBOX(thermalDebug,"AEE Debug","Thermal",false);

// The per-module trace switch, same line every other diagnostics-capable
// addon carries.  AEE_LOG_DEBUG reads the name built from the component,
// aee_<component>_logDebug, so declaring it here is what makes
// QGVAR(logDebug) resolve for thermal.  Without it thermal DEBUG output
// could only be switched on through core's flag.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Thermal",false);

// ── Solver cadence ────────────────────────────────────────────────────────
// The object-temperature scan is the most expensive call in the environment
// tick. Surface temperatures run on time constants of 600 s and up, so the
// scan does not need the tick rate. 0 restores a scan every tick.
AEE_SETTING_SLIDER(objectScanInterval,"AEE Thermal","Solver",0,120,30,0);

// ── Repaint cadence ─────────────────────────────────────────────────────────
// setObjectTexture re-uploads a procedural texture per selection, and the
// engine charge lands on the render thread where no SQF timer can see it.
// 1 repaints every frame, 30 repaints about twice a second. The physics still
// solves every pass, so the AGC and every thermal coupling are unaffected.
AEE_SETTING_SLIDER(repaintHz,"AEE Thermal","Display",1,30,4,1);

// ── Display mapping (issue #204 rework) ───────────────────────────────────
// The display carries one scalar per pixel.  Automatic mode uses the scene
// AGC (fnc_updateThermalAGC).  Manual mode uses the fixed window below.
// Real thermography and TWS devices expose manual level and span, so manual
// is physical.  The device library publishes NETD, resolution and refresh
// rate, but NO span, so the span is a user setting.
//
// Local mode normalises ONE object to its own selection radiance range, so
// that object's parts span the full palette.  It widens one object's
// contrast but breaks comparison between objects (a hot and a cold object
// can map to the same ramp), so it is opt-in and never the default.  A
// per-object gain cap of 8 times still applies, so a flat object is not
// inflated into invented contrast.
[
    QGVAR(thermalDisplayMode),
    "LIST",
    [LLSTRING(thermalDisplayMode_Name), LLSTRING(thermalDisplayMode_Description)],
    ["AEE Thermal", "Display"],
    [[0, 1, 2], ["Automatic (AGC)", "Manual", "Local (per object)"], 0],
    true,
    {}
] call CBA_fnc_addSetting;

// The palette.  Ember is the default: it interpolates the engine's own
// decoded TI colours (fnc_thermalPalette).  Grey is the luminance form.
[
    QGVAR(thermalPalette),
    "LIST",
    [LLSTRING(thermalPalette_Name), LLSTRING(thermalPalette_Description)],
    ["AEE Thermal", "Display"],
    [[0, 1, 2, 3, 4, 5, 6], ["Ember", "White hot grey", "Isotherm red", "Isotherm green", "Isotherm yellow", "Isotherm magenta", "Sepia"], 0],
    true,
    {}
] call CBA_fnc_addSetting;

// Rain on the objective lens (MKK thermal_improvement, workshop 3753145363).
// The value is the maximum lens blurriness the WetDistortion effect reaches
// at full wet; the display scales it from 0 by AEE's own rain and fog, so a
// dry scene shows nothing.
AEE_SETTING_SLIDER(thermalWetDistortion,"AEE Thermal","Display",0,1,0.08,2);

// Thermal sensor pixelation (MKK thermal_improvement, workshop 3753145363).
// Off by default, as in MKK's base preset.  On, the display quantises to the
// fitted device's vertical resolution, so a low-resolution sensor shows the
// blocks its detector actually resolves.  The device figure is never
// invented; the engine clamps a figure finer than the render.
AEE_SETTING_CHECKBOX(thermalPixelation,"AEE Thermal","Display",false);

// Manual window, in apparent surface temperature (C).  Wide by design so
// fires and exhaust stay on scale.  The code swaps the endpoints when the
// maximum is not above the minimum.
AEE_SETTING_SLIDER(thermalManualMinC,"AEE Thermal","Display",-80,200,-40,1);
AEE_SETTING_SLIDER(thermalManualMaxC,"AEE Thermal","Display",-40,600,120,5);

// ── Sensor imperfections (image realism) ──────────────────────────────────
// Real FLIR artefacts the engine does not model: a non-uniformity (NUC)
// drift of the fixed-pattern noise, temporal sensor noise, an automatic-gain
// hunt, and a bloom on hot sources.  The existing FPN and NETD term is reused.
AEE_SETTING_SLIDER(thermalTemporalNoise,"AEE Thermal","Sensor",0,2,1,0.1);
AEE_SETTING_SLIDER(thermalAgcHunt,"AEE Thermal","Sensor",0,0.1,0.05,0.005);
AEE_SETTING_SLIDER(thermalAgcHuntPeriod,"AEE Thermal","Sensor",1,20,4,1);
AEE_SETTING_SLIDER(thermalNucDrift,"AEE Thermal","Sensor",0,0.3,0.15,0.05);
AEE_SETTING_SLIDER(thermalHotBloom,"AEE Thermal","Sensor",0,0.15,0.08,0.01);
AEE_SETTING_CHECKBOX(thermalImperfectionsEnabled,"AEE Thermal","Sensor",true);
