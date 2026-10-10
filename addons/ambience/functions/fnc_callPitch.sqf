#include "..\script_component.hpp"

/*
Call-pitch kernel (wildlife ecology, task T28).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It returns the pitch multiplier for one call, deterministic from the seed, the
species, the air temperature and the relative radial velocity.  There is no
fixed pitch anywhere in the wildlife sound path.

Model, three terms on one base pitch:
  - Seeded per-call distribution.  A live animal does not repeat one pitch.
    The seed and the species length give a stable value in -1 to 1, scaled by
    the jitter spread.  The mean is 1.
  - Doppler.  A source moving toward the listener raises the received pitch
    and a receding source lowers it.  The shift is c / (c - v) with c the LOCAL
    speed of sound and v the radial velocity of the emitter toward the
    listener (positive closing).  c = 20.05 * sqrt(T + 273.15) m/s, SOURCED
    (the dry-air speed of sound).  The velocity is clamped below c.
  - Species.  A bird call pitch falls as the body grows, so an owl is lower
    than a songbird.  The factor is a per-guild constant, UNSOURCED, because
    no body mass is held.  A cricket and a cicada stridulate, and the
    stridulation rate follows the Dolbear relation T_C = 5 + N8 (SOURCED,
    held in the corpus); the pitch coupling to that rate is UNSOURCED.

Constants: c from temperature is SOURCED.  The jitter spread, the pitch
bounds, the guild factors and the stridulation pitch coupling are UNSOURCED.

Arguments:
  0: Number - the seed
  1: String - the species sound group
  2: Number - the air temperature, Celsius
  3: Number - the radial velocity toward the listener, m/s, positive closing
  4: Number - the base pitch, default 1

Returns:
  Number - the pitch multiplier, clamped to the pitch bounds
*/

params [
    ["_seed", 0, [0]],
    ["_species", "", [""]],
    ["_temperatureC", 15, [0]],
    ["_radialVelocity", 0, [0]],
    ["_basePitch", 1, [0]]
];

private _contains = {
    params ["_haystack", "_needle"];
    private _h = toLower _haystack;
    private _n = toLower _needle;
    private _hl = count _h;
    private _nl = count _n;
    if (_nl > _hl) exitWith { false };
    if (_nl <= 0) exitWith { false };
    private _found = false;
    for "_i" from 0 to (_hl - _nl) do {
        if ((_h select [_i, _nl]) == _n) then { _found = true; };
    };
    _found
};

// The species factor by guild token.  A factor of -1 marks a stridulator,
// whose term comes from the temperature instead.  Every factor is UNSOURCED.
private _GUILD_PITCH = [
    ["cricket", -1],
    ["cicada", -1],
    ["frog", 0.95],
    ["owl", 0.85],
    ["bird", 1.10],
    ["deer", 0.82],
    ["wolf", 0.82],
    ["gull", 1.05],
    ["hen", 1.02],
    ["dog", 0.95],
    ["sheep", 0.92]
];

// Local speed of sound, SOURCED: the dry-air relation c = 20.05*sqrt(T_K).
private _speedOfSound = 20.05 * (sqrt (_temperatureC + 273.15));

// Doppler: c / (c - v), with v clamped well below c so the ratio stays finite.
private _limit = _speedOfSound * 0.9;
private _v = (_radialVelocity max (-_limit)) min _limit;
private _doppler = _speedOfSound / (_speedOfSound - _v);

// Seeded per-call jitter in -1 to 1.
private _hash = (((_seed * 37) + (count _species * 11)) mod 2001);
private _unit = ((_hash / 1000) - 1);
private _jitter = 1 + (_unit * WILDLIFE_PITCH_JITTER);

// The species term.
private _speciesTerm = 1;
private _stridulator = false;
for "_g" from 0 to ((count _GUILD_PITCH) - 1) do {
    private _row = _GUILD_PITCH select _g;
    if (([_species, _row select 0] call _contains)) then {
        if ((_row select 1) < 0) then {
            _stridulator = true;
        } else {
            _speciesTerm = _row select 1;
        };
    };
};

if (_stridulator) then {
    // The Dolbear rate in chirps per minute, N8 = 7*T - 30, and its value at
    // 20 C.  The pitch coupling to the rate is UNSOURCED.
    private _rate = ((7 * _temperatureC) - 30) max 0;
    private _rateRef = 110;
    _speciesTerm = 1 + (WILDLIFE_PITCH_RATE_COUPLING * ((_rate / _rateRef) - 1));
};

private _pitch = _basePitch * _doppler * _jitter * _speciesTerm;
((_pitch max WILDLIFE_PITCH_MIN) min WILDLIFE_PITCH_MAX)
