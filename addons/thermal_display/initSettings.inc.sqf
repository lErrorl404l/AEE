// initSettings.inc.sqf - CBA Settings registration for aee_thermal_display
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// thermal_display stringtable.

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
AEE_SETTING_CHECKBOX(thermalFPN,"AEE Thermal Display","Display",true);
// Runtime kill switch for the thermal post-process chain.  The five effects are
// FULL-SCREEN render passes (two of them blurs), and they are the only engine
// render work AEE adds in thermal beyond the engine's own thermal pass.  Turning
// this off isolates that cost in-game, with no rebuild.  Default on.
AEE_SETTING_CHECKBOX(thermalPPEffects,"AEE Thermal Display","Display",true);

// ── Repaint cadence ─────────────────────────────────────────────────────────
// setObjectTexture re-uploads a procedural texture per selection, and the
// engine charge lands on the render thread where no SQF timer can see it.
// 1 repaints every frame, 30 repaints about twice a second. The physics still
// solves every pass, so the AGC and every thermal coupling are unaffected.
AEE_SETTING_SLIDER(repaintHz,"AEE Thermal Display","Display",1,30,4,1);

// Rain on the objective lens (MKK thermal_improvement, workshop 3753145363).
// The value is the maximum lens blurriness the WetDistortion effect reaches
// at full wet; the display scales it from 0 by AEE's own rain and fog, so a
// dry scene shows nothing.
AEE_SETTING_SLIDER(thermalWetDistortion,"AEE Thermal Display","Display",0,1,0.08,2);

// Thermal sensor pixelation (MKK thermal_improvement, workshop 3753145363).
// Off by default, as in MKK's base preset.  On, the display quantises to the
// fitted device's vertical resolution, so a low-resolution sensor shows the
// blocks its detector actually resolves.  The device figure is never
// invented; the engine clamps a figure finer than the render.
AEE_SETTING_CHECKBOX(thermalPixelation,"AEE Thermal Display","Display",false);

// ── Sensor imperfections (image realism) ──────────────────────────────────
// Real FLIR artefacts the engine does not model: a non-uniformity (NUC)
// drift of the fixed-pattern noise, an automatic-gain hunt, and a bloom on
// hot sources.  The temporal sensor noise and the existing FPN and NETD term
// stay with the solver in aee_thermal.
AEE_SETTING_SLIDER(thermalAgcHunt,"AEE Thermal Display","Sensor",0,0.1,0.05,3);
AEE_SETTING_SLIDER(thermalAgcHuntPeriod,"AEE Thermal Display","Sensor",1,20,4,1);
AEE_SETTING_SLIDER(thermalNucDrift,"AEE Thermal Display","Sensor",0,0.3,0.15,2);
AEE_SETTING_SLIDER(thermalHotBloom,"AEE Thermal Display","Sensor",0,0.15,0.08,2);
AEE_SETTING_CHECKBOX(thermalImperfectionsEnabled,"AEE Thermal Display","Sensor",true);

// The per-module trace switch, same line every other diagnostics-capable
// addon carries.  AEE_LOG_DEBUG reads the name built from the component,
// aee_<component>_logDebug, so declaring it here is what makes
// QGVAR(logDebug) resolve for thermal_display.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Thermal Display",false);
