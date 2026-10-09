# AEE Workshop Adopt Plan

Plan. No file was copied into the repository. Compiled 2026-10-08.

Purpose: turn `workshop-mod-licence-survey.md` (20 adoptable mods) into a per-mod decision: what AEE takes, what it must not, and why.

Method: read the licence survey, unpacked all 20 mods' PBOs with `hemtt utils pbo unpack` into `the unpacked Workshop mod tree` (1.3 GB, 5,992 SQF files), read the mod readmes, licences, function lists and key function bodies, and cross-read AEE's own module functions and ADRs. Evidence is the local Workshop tree plus the AEE repo.

## 0. Correction to the survey (acts before everything else)

**Mod 3800537038 "ACE Environment Extended" is this project.** Its `mod.cpp` action and author are `https://github.com/lErrorl404l/AEE` and `lErrorl404l`. The AEE git remote is `git@github.com:lErrorl404l/AEE.git`. The mod ships the same 20 PBOs (`aee_atmos`, `aee_thermal`, `aee_mobility`, `aee_compat_ace3`, ...) under the same `z\aee\addons\*` prefix as this repo. The survey classified it GPL-3.0; its local `LICENSE` is GPL-2.0-or-later.

Consequence: 3800537038 is **not an external adoptable mod**. It is AEE's own Workshop distribution. There is nothing to lift and no attribution to add. Treat the adoptable set as **19 external mods**, not 20. The one real risk it carries is a hard namespace collision: two copies of the same `z\aee\` PBO set cannot load together. AEE must be the single source.

---

## 1. Per-mod decisions

Each entry: what it does, the AEE module it overlaps, the specific lift (named paths), and where AEE is already ahead so the lift does not regress it.

### 1.1 CBA_A3 (450814997, GPL-2.0) - verdict: KEEP AS DEPENDENCY, LIFT NOTHING

- **What it does:** the compatibility base layer. The XEH pre-start/pre-init/post-init event chain, the function ownership primitive, the settings framework, keybinds, network events, state machines.
- **AEE overlap:** every module. AEE already hard-requires CBA: `addons/lib/config.cpp` lists `requiredAddons[] = {"A3_Data_F","cba_main","cba_xeh"}`, and every component uses the CBA macros.
- **Specific lift:** none that is worth a fork. The only candidates are already consumed through the dependency:
  - `cba_xeh/script_macros_common.hpp` - `PREP`/`FUNC`/`EFUNC`/`PATHTO_FNC` (AEE uses these).
  - `cba_xeh/fnc_compileFunction.sqf` - the ownership primitive (AEE has its own `aee_core_ownershipSentinels`, ADR-027).
  - `cba_settings/fnc_addSetting.sqf` - the settings taxonomy (AEE owns this via ADR-012 and `initSettings.inc.sqf`).
  - `cba_events/fnc_globalEvent.sqf` / `fnc_targetEvent.sqf` - the network event surface (AEE calls these).
- **Where AEE is ahead:** AEE's owned settings taxonomy (ADR-012), ownership sentinels (ADR-027), deterministic random and engine handlers (`addons/core/functions/`). None of this comes from CBA.
- **Attribution:** none. CBA is linked at runtime, not copied. GPL-2.0.
- **Do not:** vendor CBA. Copying it into AEE makes a permanent fork of an actively maintained 30-PBO project.

### 1.2 ACE3 (463939057, GPL-2.0; subfolders APL/CC-BY/CC0) - verdict: MERGE

- **What it does:** the modular realism reference. Medical (state machine, vitals, treatment), advanced ballistics, advanced fatigue, interaction menu, arsenal, compat adapters.
- **AEE overlap:** `ballistics`, `thermal`, `physiology`, `optics`, `armour`, `material`; `compat_ace3` integrates today.
- **Specific lift:**
  - **Compat-adapter pattern:** the `requiredAddons` + `skipWhenMissingDependencies` guard used in 142 configs, e.g. `ace_medical_vitals/config.cpp`. AEE should keep this exact guard shape in `addons/compat_*` so a lifted module degrades cleanly when ACE is absent.
  - **Medical state machine:** `ace_medical_status/functions/fnc_setCardiacArrestState.sqf`, `fnc_setUnconsciousState.sqf`, `fnc_getBloodPressure.sqf`, `fnc_getCardiacOutput.sqf`, `fnc_updateWoundBloodLoss.sqf`, `fnc_adjustPainLevel.sqf`. This is the one realism domain AEE does not model itself.
  - **Treatment flow:** `ace_medical_treatment/functions/fnc_treatment.sqf`, `fnc_tourniquet.sqf`, `fnc_surgicalKitProgress.sqf`. Take the stage/progress model, not the ACE item UI.
  - **Interaction-menu extension points:** `ace_interact_menu/functions/fnc_addActionToClass.sqf` and the self/vehicle action registration surface.
  - **Ballistics cross-check values:** `ace_advanced_ballistics/functions/fnc_calculateAmmoTemperatureVelocityShift.sqf`, `fnc_calculateBarrelLengthVelocityShift.sqf`, `fnc_calculateRetardation.sqf`, `fnc_calculateStabilityFactor.sqf`. Use these to validate AEE's own `addons/ballistics/functions/` numbers, not to replace them.
- **Where AEE is ahead:** `addons/ballistics` (drag tables, Coriolis, propellant sensitivity, interior ballistics), `addons/thermal` (two-band LWIR/MWIR, ADR-019), `addons/nightvision` (tube model, AGC, pincushion, scintillation, ADR-009), `addons/optics` (symbology, map, ADR-023/24/26/28/29), `addons/maritime`, `addons/wildlife`. Do not swap any of these for the ACE equivalent.
- **Attribution:** GPL-2.0. Each lifted file keeps GPL and gains a header naming ACE3, its Workshop id 463939057 and the upstream version (3.21.2.113).
- **Do not copy:** `addons/apl/` (the Arma Public License is not a free licence and is not GPL-compatible), `addons/*/sounds/` under CC-BY-3.0 (fastroping/tagging), CC-BY-4.0 (refuel) and CC0 (wardrobe). Those keep their own terms and are outside the GPL grant.

### 1.3 Zeus Enhanced / ZEN (1779063631, GPL-3.0) - verdict: MERGE (low priority)

- **What it does:** a rewritten Zeus/Eden UX: per-object attribute registration, Zeus modules, context menu, garage, markers tree.
- **AEE overlap:** none directly. This is editor/Zeus UX, not environment realism.
- **Specific lift:**
  - `zen_attributes/initAttributes.inc.sqf` - the declarative `[category, label, type, args, apply, get, condition] call FUNC(addAttribute)` registration pattern.
  - `zen_common/functions/fnc_addAttribute.sqf`, `fnc_addButton.sqf`, `fnc_addDisplay.sqf` - the registry behind it.
- **Where AEE is ahead:** AEE's map/symbology/topography (ADR-023/24/26/28/29) already exceeds ZEN's marker tree. ZEN adds no env realism. AEE also has no Zeus UI at all, so the lift is additive, not a regression.
- **Attribution:** GPL-3.0. If a GPL-3.0-only file is absorbed, AEE treats that file as GPL-3.0 and the project aggregate stays GPL-2.0-or-later (the "or later" route).

### 1.4 ACRE2 (751965892, GPL-3.0) - verdict: SKIP

- **What it does:** the full radio simulation: channel/PTT/antenna model, spatialised VOIP, TeamSpeak 3 integration, radio inventory.
- **AEE overlap:** `addons/radio` (only `calculateIonosphericAbsorption`, `calculateRadioPropagation`, `dumpState` - a propagation physics model).
- **Specific lift if any:** `acre_sys_radio/functions/fnc_canUnitTransmit.sqf`, `fnc_canUnitReceive.sqf`, `fnc_getRadioVolume.sqf`, `acre_sys_core/functions/fnc_switchChannelFast.sqf`. The data model is portable SQF.
- **Why SKIP:** the value of ACRE is the TS3/VOIP plugin (`ACRE2Steam.dll`, `acre_x64.dll`, `plugin/`). That is an external native binary and is not portable into AEE. Lifting only the SQF shell without the audio backend produces a radio that does not carry voice. The effort is enormous and the payoff is outside AEE's declared realism domains.
- **Where AEE is ahead:** the ionospheric-absorption and radio-propagation physics are AEE's own and ACRE lacks them. Do not replace them.
- **Attribution:** GPL-3.0, if any SQF is lifted.

### 1.5 Enhanced Movement Rework / EMR (2034363662, GPL-2.0) - verdict: MERGE

- **What it does:** a lightweight on-foot movement and climbing state machine (climb, vault, jump, stamina), reusing existing animations without the original Enhanced Movement's baggage.
- **AEE overlap:** `addons/mobility`. But AEE mobility is **vehicle** physics (soil bearing, mud accretion, rollover, engine load, airframe) - there is no on-foot movement layer.
- **Specific lift:**
  - `emr_main/functions/fnc_canClimb.sqf`, `fnc_startClimbing.sqf`, `fnc_climb.sqf`, `fnc_updateWalkableSurface.sqf`, `fnc_addWalkableSurfaceExitCondition.sqf`.
  - `emr_main/functions/fnc_jump.sqf`, `fnc_getStamina.sqf`, `fnc_setStamina.sqf`.
  - `emr_main/CfgMoves.hpp` and `keybinding.hpp` for the animation bindings.
- **Where AEE is ahead:** AEE's vehicle mobility (`addons/mobility/functions/calculateSoilBearingStrength.sqf`, `calculateRolloverThreshold.sqf`, `applyAccretionMass.sqf`) is far deeper than EMR. EMR is a separate, additive on-foot layer; it must not touch the vehicle model.
- **Attribution:** GPL-2.0.

### 1.6 KAT Advanced Medical (2020940806, GPL-3.0) - verdict: MERGE

- **What it does:** a medical extension on top of ACE: airway, breathing, circulation, vitals, hypothermia, pharmacology, surgery, stretcher.
- **AEE overlap:** `addons/physiology` (oxygen, altitude, dive, clothing, strain, core body temp) and `compat_kat` (`integrateKAT`). AEE has no wound/treatment state machine.
- **Specific lift - model, not UI:**
  - `kat_airway/functions/fnc_checkAirway.sqf`, `fnc_handleAirway.sqf`, `fnc_handlePuking.sqf`, `fnc_handleRecoveryPosition.sqf`.
  - `kat_breathing/functions/fnc_checkBreathing.sqf`, `fnc_checkPulseOximeter.sqf`, `fnc_createTamponade.sqf`.
  - `kat_circulation/functions/fnc_AED_Analyze.sqf`, `fnc_AED_Shock.sqf`, `fnc_handleCardiacFunction.sqf` (in `kat_vitals`).
  - `kat_vitals/functions/fnc_handleUnitVitals.sqf`, `fnc_handleTemperatureFunction.sqf`, `fnc_hasStableVitals.sqf`.
  - `kat_hypothermia/functions/fnc_checkTemperature.sqf`, `fnc_applyFluidWarmer.sqf`.
  - `kat_pharma/functions/fnc_medication.sqf`, `fnc_coagRegen.sqf`, `fnc_getBloodVolumeChange.sqf`.
- **Where AEE is ahead:** `addons/physiology` is a general physiology model (hypoxia, decompression, strain) that KAT does not have. KAT is a treatment model; the two compose. Keep AEE's physiology as the substrate.
- **Attribution:** GPL-3.0. The local `LICENSE` file governs; the Workshop page's APL-SA claim is wrong and is overridden by the shipped licence file (survey note).
- **Do not:** port the KAT item/GUI assets or the RHS compat pbos.

### 1.7 LAMBS_Danger.fsm (1858075458, GPL-2.0) - verdict: MERGE (strongest candidate)

- **What it does:** an AI tactical layer: buildings as terrain, a danger FSM, suppression response, flanking, CQB, information sharing.
- **AEE overlap:** `addons/ai` (agent sense/decide/stimulus/disturbance - a perception model, not a tactical FSM).
- **Specific lift:**
  - `lambs_danger/scripts/lambs_danger.fsm` and `lambs_dangerCivilian.fsm` - the FSM graphs.
  - `lambs_danger/functions/fnc_brainAssess.sqf`, `fnc_brainEngage.sqf`, `fnc_brainReact.sqf`, `fnc_brainHide.sqf`, `fnc_brainVehicle.sqf`.
  - `lambs_danger/functions/fnc_tacticsAssess.sqf`, `fnc_tacticsAssault.sqf`, `fnc_tacticsFlank.sqf`, `fnc_tacticsCQB.sqf`, `fnc_tacticsGarrison.sqf`.
  - `lambs_main/functions/fnc_findBuildings.sqf`, `fnc_shareInformation.sqf`, `fnc_findClosestTarget.sqf`.
  - `lambs_eventhandlers/functions/fnc_explosionEH.sqf` - the suppression/suppression-driven state change.
- **Where AEE is ahead:** `addons/ai` owns perception (`agentSense`, `stimulusDecay`, `disturbanceApply`) and `addons/wildlife` owns ecology. LAMBS is the tactical decision layer above perception; the two are complementary and do not overlap.
- **Attribution:** GPL-2.0 specifically (v2). Note the conflict: the Workshop page says "Reuploading to Steam Workshop is not permitted". GPL governs copying of code; AEE must not re-upload the LAMBS mod itself, only incorporate code under GPL. Cite both in the ADR.

### 1.8 Advanced Grappling (3123207499, GPL-2.0) - verdict: MERGE (with AUR)

- **What it does:** throwable and 40mm grappling hooks that raycast a surface, spawn a rope, and integrate with Advanced Urban Rappelling.
- **AEE overlap:** none. AEE has no climbing system.
- **Specific lift:**
  - `ag_grappling/functions/fnc_findRappelPoint.sqf` - the up-to-40-raycast surface/edge search. This is the valuable kernel.
  - `ag_grappling/functions/fnc_spawnRope.sqf`, `fnc_getClosestRope.sqf`, `fnc_rappel.sqf`, `fnc_removeNearbyRope.sqf`.
  - `ag_compat_ace/functions/` - the optional ACE-throw adapter (shows the guarded optional-dependency pattern).
- **Where AEE is ahead:** nothing to regress; this is a new capability.
- **Dependency note:** requires AUR (`730310357`) and CBA; ACE is optional and detected at runtime.
- **Attribution:** GPL-2.0.

### 1.9 ACRE-Persistence (3043180500, GPL-3.0) - verdict: MERGE PATTERN ONLY (low priority)

- **What it does:** saves radio channel/volume/spatial settings to `profileNamespace` and restores them on respawn.
- **AEE overlap:** none today.
- **Specific lift:**
  - `l6AA_acre/functions/fnc_saveRadioSettings.sqf`, `fnc_restoreRadioSettings.sqf`, `fnc_restoreRadiosOnRespawn.sqf` - the profile persistence pattern.
  - `l6AA_acre/XEH_postInit_client.sqf` - the respawn hook.
- **Why low priority:** it depends on ACRE2, which is a SKIP. Only useful if AEE ever builds a radio inventory. The persistence pattern itself (profileNamespace arrays, respawn restore) is small and reusable.
- **Attribution:** GPL-3.0.

### 1.10 ACE Environment Extended (3800537038) - verdict: NOT ADOPTABLE (this is AEE)

See section 0. Same project, same namespace, same author, same PBOs. Nothing to lift. The only action is to keep the namespace unambiguous.

### 1.11 ArmaFPV (3045129955, code GPL-2.0) - verdict: MERGE

- **What it does:** an FPV drone: camera, flight, signal/battery model, OSD, PP effects.
- **AEE overlap:** none. AEE has `addons/fx` (blast/particle/weather) but no drone.
- **Specific lift - code only:**
  - `ArmaFPV/functions/fn_fpv_getSignal.sqf`, `fn_fpv_handleSignal.sqf`, `fn_fpv_onSignalLost.sqf` - the signal-loss model.
  - `ArmaFPV/functions/fn_fpv_handleBattery.sqf`, `fn_fpv_handleTime.sqf` - endurance model.
  - `ArmaFPV/functions/fn_fpv_handleConnect.sqf`, `fn_fpv_createUavOnItemCheck.sqf`, `fn_fpv_addUavToInventory.sqf`.
  - `ArmaFPV/functions/fn_fpv_ppfx_start.sqf`, `fn_fpv_ppfx_update.sqf`, `fn_fpv_ppfx_stop.sqf` - the camera PP effects (re-home onto AEE's `addons/lib/functions/fnc_createPPEffect.sqf`).
- **Where AEE is ahead:** AEE's PP-effect lifecycle (`fnc_createPPEffect`/`fnc_destroyPPEffect`, ADR-010) must own the new effects.
- **Attribution:** code GPL-2.0, citing `LICENSE` and `THIRD_PARTY_NOTICES.txt`. **Do not copy assets:** `ASSET_LICENSE.txt` is APL-SA and `optionals/` are separate.
- **Do not:** copy the bundled CBA macros (`THIRD_PARTY_NOTICES.txt`); AEE already has CBA.

### 1.12 BackpackOnChest Redux (2372036642, MIT) - verdict: MERGE

- **What it does:** a chest backpack plus a back backpack, with loadout, ACE-gunbag and ACRE-radio variable preservation.
- **AEE overlap:** none. AEE has no inventory/loot layer.
- **Specific lift:**
  - `bocr_main/functions/fnc_actionSwap.sqf` (99 lines) - the swap core.
  - `bocr_main/functions/fnc_chestpackToHolder.sqf`, `fnc_chestpackLoadout.sqf`, `fnc_setBackpackLoadout.sqf` - cargo/loadout transfer.
  - `bocr_main/functions/fnc_chestpackAcreRadios.sqf` - variable preservation across the swap.
  - `bocr_main/functions/fnc_EHGetOut.sqf`, `fnc_EHGetIn.sqf`, `fnc_EHAnimDone.sqf` - the event hooks.
- **Where AEE is ahead:** nothing to regress; orthogonal. AEE's `addons/compat_ace3/fnc_getAceItemMass.sqf` already concerns item mass, so the chestpack mass handling should reuse it.
- **Dependency note:** hard-requires CBA and ACE3.
- **Attribution:** MIT - include the copyright notice and the MIT text in AEE's third-party notices.

### 1.13 Advanced Urban Rappelling / AUR (730310357, MIT) - verdict: MERGE (with Advanced Grappling)

- **What it does:** rappelling from a rope, with its own animations and sounds.
- **AEE overlap:** none.
- **Specific lift:**
  - `AUR_AdvancedUrbanRappelling/functions/fn_advancedUrbanRappellingInit.sqf` - the rope spawn, anchor-distance loop and slide physics.
  - The `anims/` `.rtm` set and `sounds/` are covered by MIT but are large binary assets. Prefer to reuse the animation names and take the SQF, or take the assets knowingly (MIT permits it with attribution).
- **Where AEE is ahead:** nothing to regress; new capability.
- **Attribution:** MIT. The `fn_advancedUrbanRappellingInit.sqf` header already carries the MIT text and "Copyright (c) 2016 Seth Duda".

### 1.14 Advanced Towing (639837898, MIT) - verdict: MERGE

- **What it does:** rope towing of vehicles, with attach/drop/pickup state and a surface-finding helper.
- **AEE overlap:** `addons/mobility` - AEE has traction, terrain drag and engine load but no vehicle-to-vehicle towing.
- **Specific lift:**
  - `addons/SA_AdvancedTowing/functions/fn_advancedTowingInit.sqf` (872 lines) - the whole implementation, readable as source (not packed).
  - Named kernels: `SA_Find_Surface_ASL_Under_Model`, `SA_Find_Surface_AGL_Under_Model`, `SA_Attach_Tow_Ropes`, `SA_Drop_Tow_Ropes`, `SA_Find_Nearby_Tow_Vehicles`, `SA_Get_Corner_Points`.
  - `addons/SA_AdvancedTowing/config.cpp` - the action/menu config.
- **Where AEE is ahead:** `addons/mobility` already models the physical load; the towing ropes should feed into `applyTerrainDrag`/`calculateTraction` rather than duplicate them.
- **Attribution:** MIT (README + file header). Copyright notice in AEE's third-party notices.

### 1.15 D.I.R.T. - Blood Textures (3525653940, MIT) - verdict: LIFT THE PATTERN ONLY

- **What it does:** one dynamic-texture-layer tile that raises a blood effect from unit damage and ACE bleeding.
- **AEE overlap:** `addons/material` (surface material, decals context).
- **Specific lift:** `dirt_compat_blood/functions/fnc_effectBloodChange.sqf` (~30 lines). This is the only file. It shows the D.I.R.T effect-callback contract: return a value in [0,1] where 0 is full effect, driven by `damage` and `ace_medical_woundBleeding`.
- **Trap:** the tile is MIT, but it **requires the D.I.R.T core framework** (mod 3518145984), which is APL-SA and restrictive. AEE can lift the ~30-line callback pattern but cannot ship or reuse the D.I.R.T framework. So this is a pattern reference, not a working system.
- **Where AEE is ahead:** `addons/material` (`getObjectMaterial`, `calculateStefanCoefficient`) is a cleaner material model. Do not import the D.I.R.T dependency.
- **Attribution:** MIT (diwako, 2025).

### 1.16 Speshal Core (3283642267, custom permissive, "no port") - verdict: SKIP

- **What it does:** a utility pack: earplugs (ACE-dependent), CHVD view-distance menu, skill, ragdoll, sector, environment, immersion.
- **AEE overlap:** `addons/core` (view distance, environment), `addons/actions`. Partial.
- **Candidate lift:** `tsp_core/scripts/earplug.sqf` (the earplug volume/`fadeSound` model), `tsp_core/scripts/chvd.sqf` (per-mode view distance), `tsp_core/scripts/environment.sqf`.
- **Why SKIP:** the licence is a custom permissive with a **"must NOT port"** clause. That clause is ambiguous and can be read as forbidding exactly what AEE wants (moving the code into another project). The earplug code also depends on ACE (`ace_hearing`). The legal risk is not worth a small utility. Reimplement from the engine surface if needed: the underlying `fadeSound`/`setViewDistance` APIs are engine-native.
- **Attribution:** would be attribution plus the no-port clause; not recommended.

### 1.17 Breach - Rewrite (3283645995, custom permissive) - verdict: MERGE (if the no-port clause is resolved)

- **What it does:** door breaching: finds door selections/animations/handles, computes push/pull, applies breach mechanics, lockpick and flashbang support.
- **AEE overlap:** none. AEE has no door system.
- **Specific lift:**
  - `tsp_breach/functions.sqf` - `tsp_fnc_breach_doors` (door discovery by config `UserActions`), `tsp_fnc_breach_data` (door id/animation/handle/hinge extraction via `selectionNames`), `tsp_fnc_breach_push` (push/pull classification).
  - The lockpick and flashbang mechanics in the same file.
- **Where AEE is ahead:** nothing to regress; new capability.
- **Caveat:** same "no port" family clause as Speshal Core. Resolve the clause before copying; otherwise reimplement the door-discovery algorithm from the engine config surface (it is documented in the code and uses public commands: `configOf`, `selectionPosition`, `animationNames`, `getVariable "bis_disabled_Door_*"`).
- **Attribution:** custom permissive, same family as Speshal Core.

### 1.18 Animate - Rewrite (3283612524, custom permissive) - verdict: MERGE (asset-heavy, lower priority)

- **What it does:** a tactical stance animation system (`ready`, `readyCombat`, `sprint`, `port`, `doorCompress`, `object`, `friend`, `tap`, `squeeze`, `pickup`) with the `.rtm` set and a config.
- **AEE overlap:** `addons/mobility`. AEE has no on-foot stance system.
- **Specific lift:** the tactical `.rtm` animations and the `CfgMoves` bindings in `tsp_animate/config.bin` are the value. The SQF is minimal. Take only if AEE wants on-foot stances; the animation assets are large.
- **Where AEE is ahead:** AEE's mobility is vehicle physics; this is additive.
- **Caveat:** same "no port" family clause; same resolution needed.
- **Attribution:** custom permissive.

### 1.19 Dust Wind Effect (1342869619, author grant) - verdict: LIFT

- **What it does:** a foliage/projectile dust blast by spawning and sweeping a hidden `WindSpawner` object upward, on a high-caliber fired event.
- **AEE overlap:** `addons/fx` (blast/particle/weather).
- **Specific lift:** `Dr_WindSpawner/DustWindEffect/fn_DustEffectFire.sqf` (~15 lines) and the `WindSpawner` vehicle class in `Dr_WindSpawner/config.bin`. The whole mod is one small function plus a vehicle class.
- **Where AEE is ahead:** `addons/fx/functions/` (blast, particle, weather) already owns the effect pipeline; route the dust through it rather than a new PFH.
- **Attribution:** author grant: "discontinued, feel free to use, modify and reupload" (Workshop page). Quote the grant text, the URL and the date in the third-party notices. Not a named licence.

### 1.20 TFN NVG Effects (3682613859, author grant) - verdict: MERGE (idea only; AEE is ahead)

- **What it does:** NVG depth-of-field focus, with a near/far focus toggle bind and an ACE progress bar.
- **AEE overlap:** `addons/nightvision`. AEE already models the NVG tube (`applyNVGTubeModel`, `nvgAgcBreathing`, `nvgPincushion`, `nvgScintillation`, `nvgBlindingEnvelope`, `nvgBlemishField`) and `teardownNvgDoF`.
- **Specific lift:** `functions/fn_adjustFocus.sqf` - the manual far/near DoF focus toggle (`PP_dof`/`PP_dof2`, `PPEffectAdjust`/`Commit`). Take the **UX idea** (a focus-adjust control), not the code; the code uses two hard-coded global PP handles and depends on ACE.
- **Where AEE is ahead:** AEE's NVG model is far deeper. Do not replace `teardownNvgDoF`/the tube model. Add focus adjustment as a parameter of AEE's own model.
- **Attribution:** author grant: "free to modify, reupload, include in modpacks, or adapt" (Workshop page). Quote the grant, URL and date.

---

## 2. Attribution requirements by licence class

- **GPL-2.0 (CBA, ACE, EMR, LAMBS, Advanced Grappling, ArmaFPV code):** a lifted file stays GPL. Add a header naming the source mod, Workshop id, author and the upstream version, and keep AEE's aggregate `GPL-2.0-or-later`. `%G?` signing and the existing SPDX header practice apply.
- **GPL-3.0 (ZEN, KAT, ACRE2, ACRE-Persistence):** identical, but the absorbed file is GPL-3.0-only. AEE's "or later" route lets the aggregate remain GPL-2.0-or-later; state this explicitly in the ADR for any GPL-3.0 file.
- **MIT (BOCR, AUR, Towing, D.I.R.T Blood):** keep the copyright notice and the MIT text. Add each to a single `THIRD_PARTY_NOTICES.md` (or the existing attribution surface). MIT is GPL-compatible and needs no per-file SPDX change beyond a source header.
- **Author grant (Dust Wind, TFN NVG):** no named licence. Quote the grant verbatim with the Workshop URL and the fetch date (2026-10-08) in the notices. Treat as permission, not a licence; record it as a deviation in `rules/cm-baseline.json`.
- **Custom permissive / no-port (Speshal family):** do not copy until the no-port clause is resolved. If copied, carry the clause text.
- **Never:** APL/APL-SA/APL-ND/ADPL-SA/CC-BY-NC-ND/GRAD APL/custom all-rights. These are not GPL-compatible (ACE `addons/apl`, ArmaFPV assets, D.I.R.T core, most of the 160 no-licence mods).

Existing attribution machinery to extend, not duplicate: `addons/symbology/data/markers/ATTRIBUTION.md`, `docs/ATTRIBUTION-terrain.md`, `data/symbology/*.json`, and `tools/make_sbom.py`.

---

## 3. Integration risk

**ACE and CBA dependence.**
- AEE already hard-requires CBA (`addons/lib/config.cpp`). That is settled. Nothing new.
- AEE does **not** require ACE; it integrates through optional `compat_ace3` (ADR-027 direction split). Lifting ACE/KAT/ACRE/BOCR code must therefore land in `addons/compat_*` behind the `isClass (configFile >> "CfgPatches" >> "ace_common")` guard, exactly as ZEN does in `zen_attributes/initAttributes.inc.sqf` and BOCR in `fnc_chestpackAcreRadios.sqf`. Do not promote ACE code into an AEE core module, or ACE becomes a hard dependency and AEE stops loading standalone.
- KAT, BOCR, ACRE2 and ACRE-Persistence all require ACE. LAMBS, EMR, Advanced Grappling, AUR and Towing require only CBA.

**Load order.**
- The engine orders addons by `CfgPatches requiredAddons`. An **independent** mod loads **before** AEE. To load **after** AEE a mod must declare `requiredAddons[] = {"aee_core"}` (or `aee_mobility`, etc.). This is the ADR-027 dependency inversion, proven live.
- Lifting code **into** AEE does not change load order: the lifted code runs as part of AEE.
- **Namespace collision:** mod 3800537038 ships the same `z\aee\addons\*` as this repo. If both are loaded the second overwrites the first. Keep AEE the single source and stop treating 3800537038 as external.

**GPL compatibility.**
- AEE is GPL-2.0-or-later and stays so (operator decision). It can absorb GPL-2.0, GPL-3.0, MIT, BSD and CC-BY. It cannot absorb APL-*, CC-BY-NC-ND or all-rights material.
- GPL-3.0-only files are absorbed via the "or later" route; record it.
- The one-way rule to remember: a GPL project can absorb MIT, but an MIT project cannot absorb GPL. Staying GPL keeps every option open. (The rel licence attempt was correctly stood down.)

**Fork risk.**
- CBA, ACE, ACRE2, ZEN, KAT and LAMBS are large, actively maintained projects. **Never vendor them.** A copy is a fork AEE must track forever. Lift narrow functions or adapters, record provenance, and keep the runtime dependency.
- For each lifted file, record upstream mod, id, version and commit, so a later upstream fix can be cherry-picked. `tools/make_sbom.py` and the extension contract already provide the surface.
- Anything that duplicates an existing AEE module diverges. Prefer porting the **algorithm** (re-expressed in AEE style) over copying the file.

---

## 4. Prioritised list: realism return over effort

Ranked by (realism gained x fit to an AEE module) / (effort x integration risk).

1. **LAMBS_Danger.fsm (1858075458, GPL-2.0) - MERGE. TOP FIVE.**
   Pure SQF, no binary, CBA-only. AEE's `addons/ai` owns perception but has no tactical FSM; LAMBS is the biggest single realism gap and the code drops straight into an existing module. Highest return, contained risk.

2. **Advanced Towing + AUR + Advanced Grappling (639837898 / 730310357 / 3123207499; MIT + MIT + GPL-2.0) - MERGE. TOP FIVE.**
   Readable source, no ACE requirement, clean licences, and AEE has no towing or climbing at all. A complete new mobility capability from three small, self-contained codebases. Advanced Grappling's `fnc_findRappelPoint.sqf` is the standout kernel.

3. **KAT + ACE medical model (2020940806 GPL-3.0, 463939057 GPL-2.0) - MERGE. TOP FIVE.**
   The largest realism domain AEE does not model: wounds, cardiac arrest, treatment. Highest absolute realism return. Cost is the highest (a full state machine) and it depends on ACE, so it lands in `compat_ace3`/`compat_kat` and needs the guarded adapter. Pair ACE's `ace_medical_status` with KAT's deeper modules.

4. **Dust Wind Effect + D.I.R.T Blood pattern (1342869619 grant, 3525653940 MIT) - LIFT. TOP FIVE.**
   Tiny files (about 45 lines total), explicit permissive grants, immediate visual realism. Route both through `addons/fx` and `addons/material`. D.I.R.T Blood is pattern-only because its host framework is APL-SA.

5. **BackpackOnChest Redux (2372036642, MIT) - MERGE. TOP FIVE.**
   Clean MIT, small (one 99-line core plus helpers), orthogonal to every AEE module, and the ACRE/ACE variable-preservation pattern is reusable for any AEE inventory work. Cost is low; the only requirement is a thin ACE/CBA guard.

**Just below the line:**
6. EMR on-foot climbing (GPL-2.0) - additive to `addons/mobility`, medium effort.
7. Breach door model (custom permissive) - high gameplay value, blocked on the no-port clause.
8. ArmaFPV drone model (GPL-2.0 code) - self-contained, medium effort, re-home PP effects.
9. ZEN attribute registry (GPL-3.0) - UX only, no realism.
10. ACRE-Persistence pattern (GPL-3.0) - only if AEE ever has radios.

**Skip:** CBA (keep as dependency), ACRE2 (NATIVE binary), ACE Environment Extended (this is AEE), Speshal Core (no-port), TFN NVG as code (AEE nightvision is ahead; take the focus-adjust idea only).

---

## 5. Action list

1. Correct the survey: 3800537038 is AEE itself. The external adoptable set is 19.
2. For each MERGE/LIFT mod, write an ADR that names the source mod, id, licence, upstream version and the exact files, then lift narrowly into the owning AEE module.
3. Keep ACE-dependent lifts inside `compat_*` with the `skipWhenMissingDependencies`/`isClass` guard; keep `requiredAddons` at `cba_main`/`cba_xeh` only.
4. Add a single `THIRD_PARTY_NOTICES.md`; extend the existing attribution surfaces (`ATTRIBUTION.md`, `docs/ATTRIBUTION-terrain.md`, `make_sbom.py`) rather than adding parallel ones.
5. Record the two author grants and the no-port clause as deviations in `rules/cm-baseline.json`.
6. Do not vendor CBA/ACE/ACRE/ZEN/KAT/LAMBS. Pin the upstream version in the provenance record for each lifted file.

## Budget

Full 219-row survey read plus 20 mods unpacked (1.3 GB, 5,992 SQF) and targeted reads. Longer than the 800-word briefing default because the task requires a per-mod decision with named paths. Evidence: local Workshop tree and the AEE repo, 2026-10-08.
