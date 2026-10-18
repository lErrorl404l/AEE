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
    listener (positive closing).  c = SOUND_SPEED_COEFF * sqrt(T + KELVIN_OFFSET) m/s, SOURCED
    (the dry-air speed of sound).  The velocity is clamped below c.
  - Species.  A tree cricket is a poikilotherm and its song carrier
    frequency rises linearly with temperature: Oecanthus henryi sings at 2.4
    kHz at 18 C and 3.3 kHz at 28 C, median 2.8 kHz (Mhatre, Bhattacharya,
    Robert and Balakrishnan 2011, J. Exp. Biol. 214:2569; linear across four
    Oecanthus species, Metrani and Balakrishnan 2005).  The recording is
    taken as made at the 23 C mid-point, so the pitch is CF(T) / CF(23 C)
    with CF = 2.4 + 0.09 (T - 18) kHz.  Other groups (a cicada's tymbal is a
    resonator, a bird is a homeotherm) carry no temperature term.

Constants: c from temperature and the cricket carrier frequency are SOURCED.
The jitter spread and the pitch bounds are playback limits.

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

// Local speed of sound, SOURCED: the dry-air relation c = SOUND_SPEED_COEFF*sqrt(T_K).
private _speedOfSound = SOUND_SPEED_COEFF * (sqrt (_temperatureC + KELVIN_OFFSET));

// Doppler: c / (c - v), with v clamped well below c so the ratio stays finite.
private _limit = _speedOfSound * 0.9;
private _v = (_radialVelocity max (-_limit)) min _limit;
private _doppler = _speedOfSound / (_speedOfSound - _v);

// Seeded per-call jitter in -1 to 1.
private _hash = (((_seed * 37) + (count _species * 11)) mod 2001);
private _unit = ((_hash / 1000) - 1);
private _jitter = 1 + (_unit * WILDLIFE_PITCH_JITTER);

// The species term: the tree-cricket carrier frequency (Mhatre et al. 2011).
private _speciesTerm = 1;
if ([_species, "cricket"] call _contains) then {
    private _cf = 2.4 + 0.09 * (_temperatureC - 18);
    private _cfRef = 2.4 + 0.09 * (23 - 18);
    _speciesTerm = (_cf max 0.1) / _cfRef;
};

private _pitch = _basePitch * _doppler * _jitter * _speciesTerm;
((_pitch max WILDLIFE_PITCH_MIN) min WILDLIFE_PITCH_MAX)
