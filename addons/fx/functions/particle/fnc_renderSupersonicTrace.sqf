#include "..\..\script_component.hpp"

/*
Refractive shock trace renderer (issue #217 follow-on).

A supersonic round steps the air density across its bow shock, and the
index of refraction of air tracks density, so the step bends light.
fnc_calculateSupersonicTrace returns that refractive index contrast in
units of 1e-4.  This function draws the contrast on the local player's own
round, using the engine's refractive billboard as the sprite.

HONESTY.  Three limits hold and none of them may be dropped from this
file.  First, the kernel models the REFRACTIVE component only.  It does
not model condensation, so this is not a vapour trail and not a
condensation trail.  Second, the kernel value is a CEILING.  A round with
a meplat carries a detached bow shock whose contrast at the surface is
lower than the ceiling, so the drawn distortion is an UPPER BOUND and
never an exact value.  Third, the step from refractive units to an alpha
is a VISUAL MAPPING chosen for legibility.  Size is no longer part of that
mapping: it is cone geometry now, and the reason follows.

THE SPRITE IS SIZED BY THE MACH CONE, AND THE OLD MAPPING HAD THE SIGN OF
THE SPEED DEPENDENCE WRONG.  The superseded mapping sized the sprite as
0.2 + 1.4 * legibility, so it WIDENED the sprite as contrast rose, and
contrast rises with speed.  The Mach cone does the opposite.  Its
half-angle is mu = asin (1 / M), which falls from 56.44 degrees at Mach
1.2 to 14.48 degrees at Mach 4.0, so the cone NARROWS as the round
accelerates.  The old mapping did the opposite, so the SIGN ERROR is in
the direction of the superseded mapping, not in the geometry.  fnc_calculateMachCone supplies mu and the cone width, and
this function multiplies that width by one visibility constant.  The old
legibility-scaled size expression and the old fixed sprite width are both
GONE.

THE VISIBILITY CONSTANT IS A RENDERING DECISION, NOT PHYSICS AND NOT AN
OPTICAL RELATION.  The true physical extent is the calibre, 5.6 mm to
25 mm, which is sub-pixel at every useful range.  At 1080p with a 60
degree horizontal field of view the focal length is 1662.8 pixels, so
pixels = size_m * 1662.8 / range_m.  A 5.56 mm object is 0.37 px at 25 m,
0.18 px at 50 m and 0.09 px at 100 m, and one pixel at 100 m spans about
60 mm.  _VISIBILITY is the single factor that lifts that sub-pixel width
to a drawn sprite.  It is DERIVED, not picked: it lifts the reference
case, the 5.56 mm round at Mach 2.76, to a stated minimum of 15 pixels at
a reference range of 100 m, so
_VISIBILITY = 15 * 100 / (1662.8 * 0.0173) = 52.2.  The 1080p, 60 degree
and 100 m figures are DECLARED references, not a measurement of the
player's display.  The kernel never sees this number and never scales its
own result.  The cap and the floor that bound the drawn size are stated at
their definitions, each with its reason.

THE TRAIL IS CO-MOVING, NOT A CONTRAIL.  The bow shock travels with the
round, and the pressure and temperature recover within a few body lengths,
so the visible structure is a few sprite widths long.  A persistent long
trail is a contrail and is unphysical.  The superseded fixed 0.4 s
particle lifetime, and the 25-drop lifetime that was written into the
rotation-velocity and weight slots instead of the lifetime slot, together
produced a trail of about 12.5 sprite widths, about 20 m at 940 m/s.  The
lifetime now sits in the lifetime slot, derives from the drop, and bounds
the LIVE SPRITE COUNT.

THE COST TRADE.  Size and spacing are coupled.  The drop interval is
_size / (2 * speed), so consecutive sprites overlap by construction, and
the lifetime derives from the drop, so the live sprite count is what is
bounded.  A smaller sprite at high Mach raises the SPAWN RATE, because
rate = 2 * speed / size.  _MIN_DROP bounds the rate at 4000 sprites per
second per trace.  Above the Mach where it binds the spacing exceeds half
a sprite and the trace is a sparse haze, not a continuous ribbon, which is
the physically honest outcome, because a sub-pixel shock cannot be a
continuous ribbon at any rate.  The overdraw is sprite count times sprite
area.  THE CAP IS A RENDERING-BUDGET LIMIT, NOT A PHYSICAL ONE: four
traces and eight live sprites each give 32 sprites, so the cap is
sqrt (190 / 32) = 2.44 m and the worst-case overdraw is the 190 square
metres measured as acceptable, well under the 642 that stuttered the
client on 27 Sep.  Above the cap the geometry STOPS GOVERNING and the cap
sets the size: a 13 mm round at Mach 1.36 wants 5.9 m and draws 2.4 m, so
its physics is decorative there.  A binding cap is named in the throttled
diagnostic, so a clamp can never be silent again.

WHY THIS IS NOT A PARTICLE PIPELINE GATE.  The shared pipeline runs on the
coarse environment interval aee_core_updateInterval, and its advect step
overwrites the velocity of every live source with the local wind.  Both
would fight an emitter parented to a fast round, so this renderer is
self-contained and does not register with fnc_registerParticleSource.

CLIENT ONLY.  The handler passes only the local player's own round, so the
source attached here is always local.  The function also refuses without
an interface, so a dedicated server creates nothing.  That guard cannot be
removed to enable a headless test: a server cannot draw cloudlets, so
creating sources there would cost memory for nothing, and the decision leg
is measured by the P65 probe instead.

The live contrast is re-read every tick from the round's CURRENT velocity,
which is argument 0 of the kernel.  The muzzle value published by the
Fired handler is deliberately not read here.

CONCURRENCY.  Several rounds can be in the air.  At most _MAX_TRACES
traces draw at once and a new shot is skipped at the cap, so a running
trace is never cut short to make room.

Arguments:
  0: projectile (OBJECT, the round to draw the trace on)
  1: ammo (STRING, the CfgAmmo classname of that round).  The Fired
     handler identifies it by SCANNING the event array, never by trusting
     an argument position, because CBA's compatibility path can swap two
     event slots.  The calibre is read from this class.  An empty class
     refuses the trace rather than drawing an invented width.
*/

params [
    ["_projectile", objNull, [objNull]],
    ["_ammo", "", [""]]
];

if (!hasInterface) exitWith {};
if (isNull _projectile) exitWith {
    AEE_LOG_WARN("supersonic trace refused: projectile is null");
};
if (_ammo isEqualTo "") exitWith {
    AEE_LOG_WARN("supersonic trace refused: no CfgAmmo class in the Fired event");
};

// Bound the cost when several rounds are airborne.
private _MAX_TRACES = 4;

private _traces = missionNamespace getVariable [QGVAR(supersonicTrace), []];
_traces = _traces select { alive (_x getOrDefault ["source", objNull]) };
if (count _traces >= _MAX_TRACES) exitWith {
    private _logMsg = format ["supersonic trace refused: %1 live at the cap of %2", count _traces, _MAX_TRACES];
    AEE_LOG_DEBUG(_logMsg);
};

// The sprite shape is declared once in CfgCloudlets and read here, so the
// engine path has a single source.
private _shape = getText (configFile >> "CfgCloudlets" >> "AEE_SupersonicTrace" >> "particleShape");
if (_shape == "") exitWith {
    AEE_LOG_WARN("supersonic trace refused: CfgCloudlets AEE_SupersonicTrace carries no particleShape");
};

// The calibre, from the ammunition class.  The engine's CfgAmmo "caliber"
// value is a NORMALISED penetration multiplier, not a millimetre value, so
// it must NOT be read as the calibre.  fnc_penetrationGate documents the
// reference pair: a 7.62 Ball round carries caliber 1.5.  The calibre is
// therefore taken from AEE's own data.  The cartridge table holds
// calibre_mm where the data body holds it.  Where the table holds no
// calibre, fnc_parseCaliber reads the diameter from the classname.  The
// last resort is a stated physical default, the 7.62x51 NATO calibre, the
// reference infantry cartridge, not a magic number.
private _DEFAULT_CALIBRE_MM = 7.62;
private _calibreMm = 0;
private _cartridge = [_ammo] call EFUNC(ballistics,getCartridgeData);
if ((count _cartridge) > 1) then { _calibreMm = _cartridge select 1; };
if (_calibreMm <= 0) then {
    private _parsed = [_ammo] call EFUNC(ballistics,parseCaliber);
    _calibreMm = _parsed select 0;
};
if (_calibreMm <= 0) then { _calibreMm = _DEFAULT_CALIBRE_MM; };

// The kernel takes air density and air temperature.  The flight is short,
// so the values are read once here rather than re-read every tick.
private _environment = call EFUNC(ballistics,getEnvironmentState);
_environment params ["_tempC", "_pressureHPa", "_rhoRel"];

private _source = "#particlesource" createVehicleLocal [0, 0, 0];
_source attachTo [_projectile, [0, 0, 0]];

private _record = createHashMapFromArray [
    ["source", _source],
    ["projectile", _projectile],
    ["contrast", 0]
];
_traces pushBack _record;
missionNamespace setVariable [QGVAR(supersonicTrace), _traces];

// The per-tick re-read and the reap sit in one loop, so a reader can see
// both together.  The loop ends when the round leaves the supersonic
// regime, dies, or outlives the sprite.  A trace the air no longer
// supports must not be forced into being.
// Diagnostics.  AEE_LOG_DEBUG is gated on the aee_fx_logDebug setting,
// AEE FX then Diagnostics, so it costs nothing until that box is ticked.
private _netId = netId _projectile;
private _logMsg = format ["supersonic trace open: %1 %2, rhoRel %3, tempC %4, calibre %5 mm, shape %6", _netId, str _projectile, _rhoRel, _tempC, _calibreMm, _shape];
AEE_LOG_DEBUG(_logMsg);

[_projectile, _source, _record, _shape, _rhoRel, _tempC, _calibreMm, _netId, _MAX_TRACES] spawn {
    params ["_projectile", "_source", "_record", "_spriteShape", "_rhoRel", "_tempC", "_calibreMm", "_netId", "_MAX_TRACES"];

    private _born = time;
    private _contrast = 1;
    private _MAX_LIFE = 3;
    private _ticks = 0;
    // 20 ticks at 0.05 s is about 1 Hz, so the fade reads as a trend in
    // the log instead of a wall of lines.
    private _LOG_EVERY = 20;
    private _nextLog = _LOG_EVERY;
    private _logMsg = "";

    // The rendering budget.  The worst case is _MAX_TRACES traces times
    // _LIVE_SPRITES live sprites each, times the drawn area, so the cap is
    // the square root of the measured budget over that product.  It is a
    // RENDERING-BUDGET limit and NOT a physical one: above it the geometry
    // stops governing and the cap sets the size.  190 square metres was
    // measured as acceptable, and 642 stuttered the client on 27 Sep.  The
    // cap also bounds tan(mu), which DIVERGES as Mach tends to 1, and the
    // kernel contrast vanishes there, so the loop leaves the supersonic
    // regime rather than let the cap dominate a visible sprite.
    private _OVERDRAW_BUDGET_M2 = 190;
    private _TRAIL_WIDTHS = 4;
    private _LIVE_SPRITES = 2 * _TRAIL_WIDTHS;
    private _MAX_SIZE = sqrt (_OVERDRAW_BUDGET_M2 / (_MAX_TRACES * _LIVE_SPRITES));

    // The floor exists because the engine does not draw a sub-pixel
    // billboard.  Below 0.35 m the sprite is under six pixels at 100 m, so
    // the floor keeps a trace the kernel supports observable.  It is a
    // rendering decision, not a physical one.
    private _MIN_SIZE = 0.35;
    private _MIN_DROP = 0.00025;

    // _VISIBILITY lifts the sub-pixel cone to a drawn sprite.  It is DERIVED
    // from a stated pixel target at a stated reference range, not picked.
    // The reference is the 5.56 mm round at Mach 2.76, which must subtend at
    // least 15 pixels at a reference range of 100 m.  The focal length is
    // the declared 1080p, 60 degree horizontal FOV value; the range and the
    // display are DECLARED references, not a measurement of the player's
    // screen.  A RENDERING DECISION, not physics and not an optical relation.
    private _FOCAL_LENGTH_PX = 1662.8;
    private _TARGET_PX = 15;
    private _REF_RANGE_M = 100;
    private _REF_MACH = 2.76;
    private _REF_CALIBRE_M = 0.00556;
    private _REF_CONE_M = (8 * _REF_CALIBRE_M) / sqrt ((_REF_MACH * _REF_MACH) - 1);
    private _VISIBILITY = (_TARGET_PX * _REF_RANGE_M) / (_FOCAL_LENGTH_PX * _REF_CONE_M);

    while {
        _contrast > 0
        && {alive _projectile}
        && {(time - _born) < _MAX_LIFE}
    } do {
        private _speed = vectorMagnitude (velocity _projectile);
        _contrast = [_speed, _rhoRel, _tempC] call EFUNC(ballistics,calculateSupersonicTrace);
        _record set ["contrast", _contrast];

        // --- The Mach cone, and the one non-physics constant -------------
        // The kernel returns mu in degrees and the cone width in metres,
        // from the round's current speed and its calibre.  The cone NARROWS
        // as the speed rises.  See the header for the superseded mapping.
        private _machCone = [_speed, _tempC, _calibreMm] call EFUNC(ballistics,calculateMachCone);
        private _muDeg = _machCone select 0;
        private _coneWidth = _machCone select 2;

        // The drawn size.  When the cap binds the geometry stops governing,
        // so keep the unclamped size and name the clamp on the log line.
        private _rawSize = _coneWidth * _VISIBILITY;
        private _size = (_rawSize min _MAX_SIZE) max _MIN_SIZE;
        private _clampNote = "";
        if (_rawSize > _MAX_SIZE) then {
            _clampNote = format [", CAPPED: the geometry wanted %1 m, the rendering budget caps it at %2 m", (round (_rawSize * 100)) / 100, (round (_MAX_SIZE * 100)) / 100];
        };

        // Alpha is the only free lever.  Fill rate is sprite count times
        // sprite area and never alpha.  This mapping is unchanged: the
        // kernel returns a contrast in units of 1e-4, and a round just past
        // Mach 1 shows faintly while about 8 units shows fully.
        private _legibility = linearConversion [0, 8, _contrast, 0, 1, true];
        _legibility = _legibility max 0;

        // The drop interval comes from the round's SPEED, not from a fixed
        // time.  A fixed interval is wrong at every speed: at 474 m/s the
        // old 0.162 s interval put a 0.49 m sprite every 77 m, which covers
        // 0.6 percent of the path.  This interval keeps consecutive sprites
        // overlapping by construction, at any speed.
        private _safeSpeed = _speed max 1;
        private _dropPhysical = _size / (2 * _safeSpeed);

        // A co-moving structure keeps a constant cross-section, so the two
        // entries of the size array carry the same calibre-derived width.
        // Neither is a fixed literal now, so a 5.56 mm and a 12.7 mm round
        // can no longer draw the same width.
        //
        // The lifetime derives from the PHYSICAL drop, so the live sprite
        // count is bounded at _LIVE_SPRITES and the trail is _TRAIL_WIDTHS
        // sprite widths at every speed.  _MIN_DROP bounds the spawn rate;
        // above the Mach where it binds the sprites stop overlapping and
        // the trace is a sparse haze rather than a ribbon.
        private _drop = _dropPhysical max _MIN_DROP;
        private _ttl = _LIVE_SPRITES * _dropPhysical;

        // The derived lifetime sits in the lifetime slot (index 4), where
        // the superseded version left a fixed 0.4 s and put the derived
        // value in the rotation-velocity and weight slots.  A shock does
        // not rotate and does not fall, so both are 0.
        _source setParticleParams [
            [_spriteShape, 1, 0, 0, 0], "", "Billboard",
            1, _ttl, [0, 0, 0], [0, 0, 0], 0, 0, 0.02, 0.02,
            [_size, _size],
            [[1, 1, 1, 0], [1, 1, 1, 0.20 + (0.55 * _legibility)], [1, 1, 1, 0]],
            [1000], 0.05, 0.02, "", "", _source
        ];
        _source setDropInterval _drop;

        // The first tick logs unconditionally, so a trace shorter than the
        // throttle period still yields one line; the 1 Hz throttle resumes
        // after it.  The clamp note rides on the same line, so a binding cap
        // is never silent.
        _ticks = _ticks + 1;
        if ((_ticks == 1) || (_ticks >= _nextLog)) then {
            _logMsg = format ["supersonic trace %1: speed %2 m/s, cone %3 deg, size %4 m, contrast %5%6", _netId, round _speed, round _muDeg, (round (_size * 100)) / 100, round (_contrast * 100), _clampNote];
            AEE_LOG_DEBUG(_logMsg);
            _nextLog = _ticks + _LOG_EVERY;
        };

        sleep 0.05;
    };

    // Name the reason, so a trace that vanishes is diagnosable rather
    // than mysterious.
    private _reason = "sprite lifetime expired";
    if (_contrast <= 0) then { _reason = "round left the supersonic regime" };
    if (!alive _projectile) then { _reason = "round destroyed" };
    _logMsg = format ["supersonic trace %1 closed after %2 ticks: %3", _netId, _ticks, _reason];
    AEE_LOG_DEBUG(_logMsg);

    // Deterministic reap.  On impact the round is gone, so the shock is
    // gone and the trace ends there.  That cut is physics, not a defect:
    // no bow shock stands off a stopped round.
    deleteVehicle _source;
    _record set ["source", objNull];

    private _live = missionNamespace getVariable [QGVAR(supersonicTrace), []];
    _live = _live select { alive (_x getOrDefault ["source", objNull]) };
    missionNamespace setVariable [QGVAR(supersonicTrace), _live];
};
