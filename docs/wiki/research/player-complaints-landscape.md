# Player-complaint landscape (issue #159)

The prioritisation map for the AEE roadmap, grounded in Steam reviews,
Reddit r/arma, and the BI feedback tracker.  The fixable-split verdict
is decision-grade: which complaints AEE can genuinely fix with physics
data, which are config/script-fixable, and which are engine-fundamental
(claiming to fix them damages credibility).

## The ranked complaints (frequency x passion)

1. **Performance/FPS** - single-threaded engine, cities, view distance
2. **AI behaviour** - stupid allies, omniscient enemies, vehicle AI
3. **Vehicle physics and damage** - fragile, explode too easily
4. DLC/monetisation (not mod-fixable)
5. **Stamina/fatigue system**
6. **Animations** - climbing, ladders, transitions
7. Audio - no occlusion, basic samples
8. Netcode/desync/hitreg
9. AI night vision/thermal perception
10. **Ballistics/zeroing confusion**
11. Ragdoll physics feel
12. Mod dependency (base game sparse)
13. Single-player campaign
14. **Explosion feel/particles**
15. Learning curve/UI

## The fixable-split verdict

### Engine-fundamental (DO NOT claim - damages credibility)

- Single-threaded performance ceiling
- Netcode/desync
- Ragdoll feel
- Sound occlusion (no engine acoustic simulation)
- AI detection core (knowsAbout)

### Physics-data-fixable (AEE's targets, ranked)

1. **Vehicle damage model** - the highest-value target.  The
   health-threshold explosion is unchanged since Operation Flashpoint.
   AEE's #126 (armour/penetration) + component-damage means no
   guaranteed explosion.  ACE3 proves the pattern.
2. **Explosion feel** - particles (#149/150/151), Blastcore proves it.
3. **Ballistics depth** - wind/drag/temperature.  VERIFIED SHIPPED: the
   ballistics addon has air density, ammo temperature, barrel state,
   coriolis deflection and crosswind functions (#130 barrel, #94 ammo
   temp - both closed).
4. **Stamina/sway** - the physiology fatigue -> animation speed link
   (setAnimSpeedCoef).  NOT YET BUILT - verified absent from the
   codebase; open target.
5. **Collision-response tuning** - the random-explosion-on-light-tap
   fix (#154 Pattern audit - closed).

### Config/script-fixable

- AI skill/precision (the "laser accurate" perception - often
  mission-maker settings)
- Suppression response (Courage skill)
- Stamina parameters
- Weapon sway
- View distance (#138 - closed)
- AI night vision/thermal

### Perception (educate, not fix)

- "AI sees through walls" - real LOS through soft cover + predicted
  fire at last position
- "Laser accurate" - mission-maker skill settings
- "Bullet drop wrong" - the model IS correct; players misunderstand
  zeroing
- "Vehicles explode too easily" - half real, half expectation of
  soft-body damage no mod delivers

## The mapping to AEE's existing work (verified current)

| Complaint | AEE issue | Status |
|---|---|---|
| Vehicle damage | #126 (armour/penetration), #107 (fragmentation) | OPEN targets |
| Explosion feel | #149/#150/#151 (particle pipeline) | OPEN |
| Ballistics | ballistics addon + #130 + #94 | SHIPPED |
| Stamina/sway | physiology + setAnimSpeedCoef | physiology shipped, coupling NOT built |
| AI | #74/#75/#81 (the AI cluster) | OPEN |
| View distance | #138 (vision-driven) | CLOSED |
| Collision response | #154 Pattern audit | CLOSED |
| Performance | #97 (monitoring), #139 (range cost), #138 | #139 OPEN |
| AI night/thermal perception | #9 in the list | OPEN |

## The roadmap order (validated by player demand)

vehicle damage -> explosion feel -> ballistics depth -> stamina/sway ->
collision-response tuning

This confirms the existing priorities: #126 (armour) is the right first
physics-data target, the particle pipeline (#149-151) delivers
explosion feel, and the AI cluster (#74/75/81) addresses the #2
complaint.

## Animation-specific notes (from the tracker)

- No climbing/vaulting (T61802, 100+ comments) - Enhanced Movement
  exists but causes a prone-reload freeze bug (real)
- Ladder animation "really horrible" (T62072)
- Reload locks movement (T72973) - regression from Arma 2
- Swimming resets firing mode to single (A3G-45, live Aug 2026)
- **The animation fix AEE CAN own**: setAnimSpeedCoef coupling -
  physiology state (dexterity %, fatigue, cold) scales movement
  animation speed.  A physics-data animation improvement no other
  mod does.  Not yet built.

## Test vectors

- Vehicle hit by small arms -> component damage, NOT guaranteed
  explosion (#126)
- Hypothermic soldier -> visibly slower movement animation
  (setAnimSpeedCoef)
- The #138 view distance lowers the #1 complaint (performance) in
  weather

## Sources

- Steam negative reviews (performance 14 mentions = top theme)
- Reddit r/arma threads (AI, vehicle, stamina)
- BI feedback tracker (T61802 climbing, T62072 ladders, T72973 reload,
  A3G-45 swimming, T170689 AI night)
- Mod feedback: ACE3, LAMBS, VCOM, Enhanced Movement, Blastcore,
  JSRS, VTO