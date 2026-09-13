#!/usr/bin/env python3
"""Scientific validation harness for the NVG depth-of-field focus system.

Mirrors the SQF implementation in fnc_applyNVGTubeModel.sqf (fan raycast,
median aggregation, O3DE auto-focus state machine) and validates it
against real optics physics and required behaviour:

  Physics (checked here):
    - Hyperfocal distance of the NVG objective: H = f^2/(N*c) + f
      (f = 27 mm, N = 1.2, CoC 25-50 um) -> H = 12-24 m
    - Near limit at the infinity setting: H/2 = 6-12 m; only objects
      closer than that blur (blur circle b = f^2/(N*s), continuous 1/s)
    - DoF band at other focus settings (thin-lens near/far limits)

  Behaviour (checked here):
    - Median aggregation: a near object covering PART of the fan does
      not drag focus off the dominant surface (no flip-flop)
    - Deadband: settled focus does not re-rack for small scene changes
    - Delay: a transient target does not trigger a rack
    - Constant-speed rack: focus glides monotonically, no teleport
    - Hold-on-empty: looking at sky keeps the current focus
    - Weapon exclusion: the operator's own weapon (< 2 m) is ignored

  NOT verifiable from code alone (engine calibration):
    - Arma's DepthOfField ppEffect param semantics ([blur, distance])
    - The absolute blur magnitude per tier
    - The exact deadband % / rack speed feel (operator calibration)

Run:  python3 tools/validation/validate_dof.py
Exit: 0 when every check passes, 1 when any fails.
"""

import math

# ─── Optics physics (from the research report) ─────────────────────────────

# NVG objective: f/1.2, ~27 mm focal length, 18 mm tube (PVS-14 class).
F_MM = 27.0
N_STOP = 1.2
# Circle of confusion = 2-4 line pairs of the tube (line-pair pitch 12-16 um
# at 62-82 lp/mm resolution).
COC_UM = (25.0, 50.0)


def hyperfocal(f_mm, n, coc_um):
    """H = f^2/(N*c) + f, all in mm -> metres."""
    return f_mm**2 / (n * (coc_um / 1000.0)) / 1000.0 + f_mm / 1000.0


def blur_circle_mm(f_mm, n, s_m):
    """b = f^2/(N*s) for object at s, focused at infinity.  mm."""
    return f_mm**2 / (n * s_m * 1000.0)


def dof_near_far(f_mm, n, coc_um, s_m):
    """Thin-lens near/far limits (m) for focus distance s."""
    h = hyperfocal(f_mm, n, coc_um) * 1000.0  # mm
    s = s_m * 1000.0  # mm
    near = s * h / (h + s) / 1000.0
    far = s * h / (h - s) / 1000.0
    if h <= s:
        far = float("inf")
    return near, far


# ─── SQF mirror: fan raycast + median aggregation + state machine ────────

FAN_COUNT = 9
NEAR_LIMIT_M = 0.25  # objective near limit (PVS-14: 25 cm)
DEADBAND_FRAC = 0.25
DEADBAND_MIN_M = 0.5
HOLD_S = 0.25
MAX_STEP_M = 1.5  # 15 m/s at 0.1 s tick
SETTLE_M = 0.1
TICK_S = 0.1


def fan_hits(scene, look_centre_deg=0.0):
    """Simulate the 9-ray fan against a scene.

    scene: list of (start_m, end_m, dist, is_player) - each surface is an
    angular band (deg offset from centre) with a distance and a flag for
    whether the hit is the operator's own model (weapon/body).
    Returns the list of valid hit distances, one per ray.
    """
    # Ray offsets: centre + 4 cardinal + 4 diagonal at ~6 deg half-angle.
    offsets = [0.0, 6.0, -6.0, 6.0, -6.0, 8.5, -8.5, -8.5, 8.5]
    hits = []
    for off in offsets:
        theta = look_centre_deg + off
        dist = None
        is_player_hit = False
        for start, end, d, is_player in scene:
            if theta >= start and theta <= end:
                dist = d
                is_player_hit = is_player
                break
        if dist is not None and not is_player_hit:
            hits.append(max(dist, NEAR_LIMIT_M))
    return hits


def median_hits(hits):
    """Mirror of the SQF: median of valid hits; empty if < half the fan."""
    if len(hits) < FAN_COUNT / 2:
        return 0.0
    s = sorted(hits)
    return s[len(s) // 2]


def state_machine(raw_target, cur_focus, pending, hold_until, t):
    """Mirror of the SQF O3DE state machine.  Returns (cur, pending, hold)."""
    deadband = max(cur_focus * DEADBAND_FRAC, DEADBAND_MIN_M)
    if raw_target > 0:
        if abs(raw_target - cur_focus) > deadband:
            if raw_target != pending:
                # Re-arm only on material change; track drift without
                # resetting the hold clock (walking player starves the
                # rack otherwise).
                if pending == 0 or abs(raw_target - pending) > 0.5:
                    pending = raw_target
                    hold_until = t + HOLD_S
                else:
                    pending = raw_target
        else:
            # Inside the band: cancel only when no rack is in flight.
            if pending == 0:
                hold_until = 0.0
    if pending > 0 and t >= hold_until:
        step = pending - cur_focus
        if abs(step) > MAX_STEP_M:
            step = MAX_STEP_M * (1.0 if step > 0 else -1.0)
        cur_focus += step
        if abs(pending - cur_focus) < SETTLE_M:
            cur_focus = pending
            pending = 0.0
            hold_until = 0.0
    return cur_focus, pending, hold_until


def run_scenario(scene_series, focus0=None, n_ticks=300):
    """Run the state machine over a time series of scenes.

    scene_series: list of scenes (one per tick) OR a list of
    (t0, t1, scene) so a scene holds for a run of ticks.
    Returns (focus_history, raw_history, raw_smooth_history).
    """
    cur = focus0 if focus0 is not None else 50.0
    pending = 0.0
    hold_until = 0.0
    raw_smooth = 0.0
    focus_hist, raw_hist, smooth_hist = [], [], []
    for i in range(n_ticks):
        t = i * TICK_S
        scene = None
        for t0, t1, sc in scene_series:
            if t0 <= t < t1:
                scene = sc
                break
        if scene is None:
            raw = 0.0
        else:
            raw = median_hits(fan_hits(scene))
        # Raw-target EMA smoothing (mirror of the SQF).  Cold start: the
        # smoother initialises from the first raw target, not from 0 - a
        # zero-initialised filter drags focus down on entry (3 m in the
        # deadband test before the guard).
        if raw_smooth <= 0:
            raw_smooth = raw if raw > 0 else 0.0
        elif raw > 0:
            raw_smooth = raw_smooth + (raw - raw_smooth) * 0.5
        else:
            raw_smooth = 0.0
        cur, pending, hold_until = state_machine(
            raw_smooth, cur, pending, hold_until, t
        )
        focus_hist.append(cur)
        raw_hist.append(raw)
        smooth_hist.append(raw_smooth)
    return focus_hist, raw_hist, smooth_hist


# ─── Checks ────────────────────────────────────────────────────────────────


def check_hyperfocal():
    """Hyperfocal distance must be ~12-24 m (research: H = 10-30 m band)."""
    results = []
    for coc in COC_UM:
        h = hyperfocal(F_MM, N_STOP, coc)
        near = h / 2
        ok = 12.0 <= h <= 30.0 and 6.0 <= near <= 15.0
        results.append((coc, h, near, ok))
    return {
        "name": "Hyperfocal distance",
        "ground_truth": "H = f^2/(N*c)+f, f=27mm f/1.2, CoC 25-50um: H=12-24m",
        "grid": f"CoC {COC_UM[0]}..{COC_UM[1]} um",
        "tolerance": "H within 12-30 m, near limit within 6-15 m",
        "status": "PASS" if all(r[3] for r in results) else "FAIL",
        "max_abs": "; ".join(f"H={h:.1f}m near={n:.1f}m" for _, h, n, _ in results),
        "rmse": 0.0,
        "unit": "m",
        "note": "Research-confirmed: everything beyond near limit sharp at infinity",
    }


def check_blur_continuous():
    """Blur circle grows continuously as 1/s (weapon smear, target sharp)."""
    s_list = [0.5, 1.0, 5.0, 10.0, 15.0]
    b_list = [blur_circle_mm(F_MM, N_STOP, s) for s in s_list]
    # Monotonic decreasing with distance, and weapon >> CoC, target < CoC.
    mono = all(b_list[i] > b_list[i + 1] for i in range(len(b_list) - 1))
    weapon_smear = b_list[0] > 1.0  # 0.5 m: > 1 mm blur circle
    target_ok = b_list[-1] < 0.1  # 15 m: < 0.1 mm, near the CoC band
    return {
        "name": "Blur circle continuous 1/s",
        "ground_truth": "b = f^2/(N*s): 0.5 m -> 1.2 mm (smear), 15 m -> 0.04 mm",
        "grid": "s = 0.5..15 m",
        "tolerance": "monotonic, weapon > 1 mm, 15 m < 0.1 mm",
        "status": "PASS" if mono and weapon_smear and target_ok else "FAIL",
        "max_abs": "; ".join(f"{s}m->{b:.3f}mm" for s, b in zip(s_list, b_list)),
        "rmse": 0.0,
        "unit": "mm",
        "note": "Continuous falloff, not binary near/far - matches operator reports",
    }


def check_dof_band_moves():
    """The DoF band moves with the focus ring (thin-lens equations)."""
    near1, far1 = dof_near_far(F_MM, N_STOP, 25.0, 5.0)
    near2, far2 = dof_near_far(F_MM, N_STOP, 25.0, 20.0)
    # 5 m focus: 4.1-6.3 m band (tight, near objects only).
    # 20 m focus: ~11 m to 112 m (CoC 25 um) - much deeper, far side open.
    band1 = far1 - near1
    band2 = far2 - near2
    ok = near2 > 10.0 and far2 > 100.0 and band2 > band1 * 5
    return {
        "name": "DoF band moves with focus",
        "ground_truth": "5 m focus: 4.1-6.3 m (tight); 20 m focus: 11-112 m (deep)",
        "grid": "focus 5 m, 20 m",
        "tolerance": "20 m focus reaches > 100 m, band > 5x the 5 m band",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"5m: {near1:.1f}-{far1:.1f}m ({band1:.1f}m); 20m: {near2:.1f}-{far2:.1f}m ({band2:.1f}m)",
        "rmse": 0.0,
        "unit": "m",
        "note": "Focus near -> shallow band; focus far -> deep band (hyperfocal)",
    }


def check_median_no_flipflop():
    """Bush covering part of the fan must NOT drag focus off the building."""
    # Bush at 3 m covers only the centre ray (1/9, angular width +-3 deg
    # keeps the +-6 cardinal rays on the building).  The building at 20 m
    # covers the remaining 8.  Median must be 20 m.
    scene = [
        (-3.0, 3.0, 3.0, False),
        (3.0, 12.0, 20.0, False),
        (-12.0, -3.0, 20.0, False),
    ]
    hits = fan_hits(scene)
    med = median_hits(hits)
    ok = med == 20.0
    return {
        "name": "Median aggregation - no flip-flop",
        "ground_truth": "Dominant surface (building, 8/9 rays) wins over centre-only bush (1/9)",
        "grid": "bush 3 m (1 ray, +-3 deg) in front of building 20 m (8 rays)",
        "tolerance": "median == 20 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"median={med} m, hits={sorted(hits)}",
        "rmse": 0.0,
        "unit": "m",
        "note": "Nearest-hit would return 3 m and flip-flop as the bush enters/leaves",
    }


def check_bush_dominant():
    """Bush covering MOST of the fan genuinely dominates focus."""
    # Bush at 3 m covers +-7 deg (5 rays: centre + both +-6 cardinal + both
    # 8.5 diagonals), the building the remaining 4.  Median must be 3 m.
    scene = [
        (-7.0, 7.0, 3.0, False),
        (7.0, 12.0, 20.0, False),
        (-12.0, -7.0, 20.0, False),
    ]
    hits = fan_hits(scene)
    med = median_hits(hits)
    ok = med == 3.0
    return {
        "name": "Dominant near object focuses",
        "ground_truth": "Bush covering 5+ rays is the target area's dominant surface",
        "grid": "bush 3 m (5 rays) dominates building 20 m (4 rays)",
        "tolerance": "median == 3 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"median={med} m, hits={sorted(hits)}",
        "rmse": 0.0,
        "unit": "m",
        "note": "Median tracks what is actually dominant, not the far outlier",
    }


def check_weapon_exclusion():
    """Hits on the operator's own model (weapon) are excluded by identity."""
    # Weapon at 0.7 m (is_player=True) covers the centre ray only.
    scene = [
        (-1.0, 1.0, 0.7, True),
        (1.0, 12.0, 25.0, False),
        (-12.0, -1.0, 25.0, False),
    ]
    hits = fan_hits(scene)
    ok = 0.7 not in hits and len(hits) == 8
    return {
        "name": "Weapon exclusion by object identity",
        "ground_truth": "Operator focuses past the weapon; own-model hits ignored",
        "grid": "weapon 0.7 m (centre ray, is_player) + wall 25 m",
        "tolerance": "no 0.7 m hit, all 8 non-weapon rays valid",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"hits={sorted(hits)}",
        "rmse": 0.0,
        "unit": "m",
        "note": "Was a 2 m distance cut that snapped close objects; now identity",
    }


def check_blur_gate():
    """Close objects track down to the near limit, then blur gradually.

    The 'blur gate': as the player approaches a real object the focus
    tracks it (object identity, no distance cut), so the object stays in
    focus down to the objective's 25 cm near limit.  There is no sharp
    clear->blurry transition at an arbitrary distance - the DoF band
    falls off continuously, and only objects closer than the NEAR LIMIT
    (physically impossible to focus) blur.
    """
    # Player walks toward a wall: 10 m -> 0.2 m over 30 s.
    # Scene reports the wall at the current distance, no snap.
    series = []
    for i in range(300):
        t = i * TICK_S
        d = max(10.0 - t * 0.33, 0.2)  # walk from 10 m to 0.2 m
        series.append((t, t + TICK_S, [(-12.0, 12.0, d, False)]))
    fh, rh, sh = run_scenario(series, focus0=10.0, n_ticks=300)
    # Focus must track down to the near limit smoothly (no jump > 1.5 m/tick
    # beyond the rack speed), and must NOT go below the near limit.
    steps = [abs(fh[i + 1] - fh[i]) for i in range(len(fh) - 1)]
    ok = min(fh) >= NEAR_LIMIT_M - 0.01 and max(steps) <= MAX_STEP_M + 1e-9
    return {
        "name": "Blur gate - close tracking, no snap",
        "ground_truth": "Real object tracks to 25 cm near limit; no hard cut",
        "grid": "wall 10 m -> 0.2 m over 30 s",
        "tolerance": "focus >= 25 cm always, max step <= 1.5 m/tick",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"min focus={min(fh):.2f} m, max step={max(steps):.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "The old 2 m cut snapped clear->blurry; identity exclusion tracks",
    }


def check_hold_on_empty():
    """Looking at sky (no hits) keeps the current focus, no jump."""
    # Settle on a 20 m wall, then look at sky (empty scene).
    wall = [(-12.0, 12.0, 20.0, False)]
    sky = [(-12.0, 12.0, None, False)]  # None = no surface (ray misses)
    series = [(0.0, 5.0, wall), (5.0, 30.0, sky)]
    fh, rh, sh = run_scenario(series, focus0=20.0, n_ticks=300)
    sky_focus = [f for f, r in zip(fh, rh) if r == 0.0]
    ok = all(abs(f - 20.0) < 0.2 for f in sky_focus)
    return {
        "name": "Hold-on-empty (sky)",
        "ground_truth": "A real ring stays where set; sky must not fly to infinity",
        "grid": "20 m wall 5 s, then open sky",
        "tolerance": "focus stays within 0.2 m of 20 m during sky",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"focus during sky: {sky_focus[0]:.2f}..{sky_focus[-1]:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Kills the 'snaps away and back' artefact",
    }


def check_glide_no_snap():
    """A large focus change glides monotonically, never teleports."""
    # Transition 3 m (bush) -> 20 m (building) as the player re-aims.
    bush = [(-12.0, 12.0, 3.0, False)]
    bldg = [(-12.0, 12.0, 20.0, False)]
    series = [(0.0, 2.0, bush), (2.0, 30.0, bldg)]
    fh, rh, sh = run_scenario(series, focus0=3.0, n_ticks=300)
    # Max per-tick step must be <= MAX_STEP_M (no teleport).
    steps = [abs(fh[i + 1] - fh[i]) for i in range(len(fh) - 1)]
    max_step = max(steps)
    # Must actually arrive at 20 m within the window.
    arrived = abs(fh[-1] - 20.0) < 0.2
    ok = max_step <= MAX_STEP_M + 1e-9 and arrived
    return {
        "name": "Glide - no snap",
        "ground_truth": "Constant-speed rack: 3 -> 20 m over ~1.2 s, monotonic",
        "grid": "bush 3 m then building 20 m",
        "tolerance": f"per-tick step <= {MAX_STEP_M} m AND arrives at 20 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"max step={max_step:.2f} m/tick, final={fh[-1]:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "The 40 m/s version snapped; 15 m/s glides like a ring turn",
    }


def check_deadband_stability():
    """Settled focus tolerates small scene changes (no hunting)."""
    # Wall segments at 8-12 m (median 10 m), then a small 1 m drift.
    seg = [(-12.0, 12.0, 10.0, False)]
    seg2 = [(-12.0, 12.0, 11.0, False)]  # within deadband (25% of 10 = 2.5 m)
    series = [(0.0, 2.0, seg), (2.0, 30.0, seg2)]
    fh, rh, sh = run_scenario(series, focus0=10.0, n_ticks=300)
    drift = max(abs(f - 10.0) for f in fh)
    ok = drift < 1.0  # 10 -> 11 m target is inside the 2.5 m deadband
    return {
        "name": "Deadband - no hunting",
        "ground_truth": "25% deadband: a 1 m scene drift inside the band must not rack",
        "grid": "10 m wall, then 11 m wall (inside 2.5 m deadband)",
        "tolerance": "focus drift < 1 m over the whole run",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"max drift={drift:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Stops the ring hunting on small scene changes",
    }


def check_transient_delay():
    """A transient target (branch passing) must not trigger a rack."""
    wall = [(-12.0, 12.0, 20.0, False)]
    transient = [
        (-6.0, 0.0, 3.0, False),
        (0.0, 12.0, 20.0, False),
    ]  # branch for 2 ticks
    series = [(0.0, 3.0, wall), (3.0, 3.2, transient), (3.2, 30.0, wall)]
    fh, rh, sh = run_scenario(series, focus0=20.0, n_ticks=300)
    moved = max(abs(f - 20.0) for f in fh)
    ok = moved < 1.0  # 0.25 s hold + median: a 2-tick transient must not rack
    return {
        "name": "Transient target delay",
        "ground_truth": "0.25 s hold: a branch passing the fan for 2 ticks is ignored",
        "grid": "20 m wall, 3 m branch for 0.2 s, back to wall",
        "tolerance": "focus movement < 1 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"max movement={moved:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Hold + median together reject the transient",
    }


def check_first_tick_default():
    """First tick with no target defaults to 50 m, does not break."""
    sky = [(-12.0, 12.0, None, False)]
    fh, rh, sh = run_scenario([(0.0, 30.0, sky)], focus0=None, n_ticks=30)
    ok = all(0 < f <= 60 for f in fh) and fh[0] == 50.0
    return {
        "name": "First-tick default",
        "ground_truth": "No target yet -> 50 m, then hold (empty sky)",
        "grid": "open sky from tick 0",
        "tolerance": "focus == 50 m and stays finite",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"first={fh[0]} m last={fh[-1]} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Guards against 0/infinity on the first frame",
    }


# ─── Edge cases, extremes, normals ─────────────────────────────────────────


def check_extreme_near():
    """Walking right up to a wall tracks to the near limit, no snap."""
    series = []
    for i in range(300):
        t = i * TICK_S
        d = max(3.0 - t * 0.1, 0.2)  # 3 m -> 0.2 m over 30 s
        series.append((t, t + TICK_S, [(-12.0, 12.0, d, False)]))
    fh, rh, sh = run_scenario(series, focus0=3.0, n_ticks=300)
    min_f = min(fh)
    steps = [abs(fh[i + 1] - fh[i]) for i in range(len(fh) - 1)]
    ok = min_f >= NEAR_LIMIT_M - 0.01 and max(steps) <= MAX_STEP_M + 1e-9
    return {
        "name": "Extreme near - wall to 20 cm",
        "ground_truth": "Objective near limit 25 cm; focus clamps there",
        "grid": "wall 3 m -> 0.2 m over 30 s",
        "tolerance": "focus >= 25 cm always, no step > 1.5 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"min focus={min_f:.2f} m, max step={max(steps):.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Focus must not dive below the physical near limit",
    }


def check_extreme_far():
    """Looking from close to very far racks out, holds the far surface."""
    # Building at 250 m.  Focus starts at 3 m.
    bldg = [(-12.0, 12.0, 250.0, False)]
    series = [(0.0, 1.0, [(-12.0, 12.0, 3.0, False)]), (1.0, 30.0, bldg)]
    fh, rh, sh = run_scenario(series, focus0=3.0, n_ticks=300)
    ok = (
        abs(fh[-1] - 250.0) < 0.5
        and max(abs(fh[i + 1] - fh[i]) for i in range(len(fh) - 1)) <= MAX_STEP_M + 1e-9
    )
    return {
        "name": "Extreme far - rack to 250 m",
        "ground_truth": "Constant-speed rack reaches the far surface",
        "grid": "3 m then 250 m building",
        "tolerance": "arrives at 250 m, no teleport",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"final={fh[-1]:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "247 m at 1.5 m/tick = ~16.5 s of gliding, monotonic",
    }


def check_weapon_only():
    """Looking only at the weapon (all rays on own model) holds focus."""
    # Weapon everywhere: every fan ray hits the player's own model.
    scene = [(-12.0, 12.0, 0.7, True)]
    fh, rh, sh = run_scenario([(0.0, 30.0, scene)], focus0=15.0, n_ticks=300)
    ok = all(abs(f - 15.0) < 0.2 for f in fh)  # no movement at all
    return {
        "name": "Weapon-only view holds focus",
        "ground_truth": "All rays on own model -> empty target -> hold",
        "grid": "weapon 0.7 m across the whole fan for 30 s",
        "tolerance": "focus unchanged (15 m)",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"final={fh[-1]:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Weapon must never drag or hold-lock the focus",
    }


def check_oscillating_target():
    """A target oscillating around the deadband edge does not hunt."""
    # Wall alternates 10 m and 11 m (inside the 25% deadband of ~10 m).
    a = [(-12.0, 12.0, 10.0, False)]
    b = [(-12.0, 12.0, 11.0, False)]
    series = []
    for i in range(300):
        t = i * TICK_S
        sc = a if (i // 10) % 2 == 0 else b  # flip every 1 s
        series.append((t, t + TICK_S, sc))
    fh, rh, sh = run_scenario(series, focus0=10.0, n_ticks=300)
    drift = max(abs(f - 10.0) for f in fh)
    ok = drift < 1.0
    return {
        "name": "Oscillating target - no hunting",
        "ground_truth": "Deadband absorbs 10<->11 m flip; focus stays put",
        "grid": "wall alternates 10/11 m every 1 s",
        "tolerance": "focus drift < 1 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"max drift={drift:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Edge case: deadband must swallow boundary oscillation",
    }


def check_moving_target_tracking():
    """A moving target (walking player) tracks continuously, no stall.

    Regression: the hold timer was reset every tick when the raw target
    drifted (wall moves 0.03 m per 0.1 s tick), so the rack never
    started.  The fix re-arms only on a material target change (> 0.5 m)
    and follows drift without resetting the clock.
    """
    series = []
    for i in range(300):
        t = i * TICK_S
        d = max(10.0 - t * 0.33, 0.2)  # player walks toward wall
        series.append((t, t + TICK_S, [(-12.0, 12.0, d, False)]))
    fh, rh, sh = run_scenario(series, focus0=10.0, n_ticks=300)
    ok = fh[-1] < 3.0  # must track well below the 10 m start
    return {
        "name": "Moving target tracks (walk regression)",
        "ground_truth": "Walking player: focus follows the approaching wall",
        "grid": "wall 10 m -> 0.2 m over 30 s",
        "tolerance": "final focus < 3 m (was 8.5 m before the fix)",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"final={fh[-1]:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Catches the hold-timer-reset starvation bug",
    }


def check_normal_pan():
    """A normal pan across varied terrain glides smoothly."""
    # Pan: near bush 5 m, then open field 30 m, then far ridge 80 m.
    bush = [(-12.0, 12.0, 5.0, False)]
    field = [(-12.0, 12.0, 30.0, False)]
    ridge = [(-12.0, 12.0, 80.0, False)]
    series = [
        (0.0, 8.0, bush),
        (8.0, 16.0, field),
        (16.0, 30.0, ridge),
    ]
    fh, rh, sh = run_scenario(series, focus0=5.0, n_ticks=300)
    steps = [abs(fh[i + 1] - fh[i]) for i in range(len(fh) - 1)]
    ok = abs(fh[-1] - 80.0) < 0.5 and max(steps) <= MAX_STEP_M + 1e-9
    return {
        "name": "Normal pan - smooth glide",
        "ground_truth": "5 -> 30 -> 80 m rack glides at constant speed",
        "grid": "bush 5 m (8 s), field 30 m (8 s), ridge 80 m (14 s)",
        "tolerance": "arrives at 80 m, no step > 1.5 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"final={fh[-1]:.2f} m, max step={max(steps):.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Normal use: the ring racks between targets at constant speed",
    }


def check_noise_no_hunting():
    """Median fan jitter (1-3 m, measured in the RPT) must not hunt.

    Regression: the RPT showed 122 focus re-racks in 3.5 min.  The
    median of a 9-ray fan jitters tick to tick as the view moves
    fractions of a degree; feeding the raw jitter straight into the
    state machine made it re-rack constantly.  The raw-target EMA
    (0.5 blend) removes the high-frequency churn while keeping real
    movement.  Without it, a stationary 15 m wall with +-1.5 m jitter
    re-racks ~25 times in 30 s.
    """
    import random

    random.seed(7)
    wall = [(-12.0, 12.0, 15.0, False)]
    # Jittered scene: vary the reported wall distance by +-1.5 m each
    # tick, simulating fan-median noise on a stationary view.
    series = []
    for i in range(300):
        t = i * TICK_S
        j = 15.0 + random.uniform(-1.5, 1.5)
        series.append((t, t + TICK_S, [(-12.0, 12.0, max(j, 0.5), False)]))
    fh, rh, sh = run_scenario(series, focus0=15.0, n_ticks=300)
    re_racks = sum(1 for i in range(1, len(fh)) if fh[i] != fh[i - 1])
    drift = max(abs(f - 15.0) for f in fh)
    ok = re_racks <= 8 and drift < 2.0
    return {
        "name": "Fan jitter - no hunting",
        "ground_truth": "EMA absorbs +-1.5 m median jitter; focus stays put",
        "grid": "stationary 15 m wall with +-1.5 m jitter, 30 s",
        "tolerance": "<= 8 re-racks, drift < 2 m",
        "status": "PASS" if ok else "FAIL",
        "max_abs": f"re-racks={re_racks}, max drift={drift:.2f} m",
        "rmse": 0.0,
        "unit": "m",
        "note": "Reproduces the RPT hunting; proves the EMA fix",
    }


# ─── Main ──────────────────────────────────────────────────────────────────

CHECKS = [
    check_hyperfocal,
    check_blur_continuous,
    check_dof_band_moves,
    check_median_no_flipflop,
    check_bush_dominant,
    check_weapon_exclusion,
    check_blur_gate,
    check_hold_on_empty,
    check_glide_no_snap,
    check_deadband_stability,
    check_transient_delay,
    check_first_tick_default,
    check_extreme_near,
    check_extreme_far,
    check_weapon_only,
    check_oscillating_target,
    check_moving_target_tracking,
    check_normal_pan,
    check_noise_no_hunting,
]


def main():
    fails = 0
    print("DoF focus validation harness")
    print("=" * 60)
    for check in CHECKS:
        r = check()
        mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP", "INFO": "INFO"}[
            r["status"]
        ]
        if r["status"] == "FAIL":
            fails += 1
        print(f"[{mark}] {r['name']}")
        print(f"        {r['max_abs']}")
        if r["status"] == "FAIL":
            print(f"        ground truth: {r['ground_truth']}")
            print(f"        tolerance:    {r['tolerance']}")
    print("=" * 60)
    print(f"Checks run: {len(CHECKS)}")
    print(f"Failed: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
