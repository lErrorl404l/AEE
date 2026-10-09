#include "..\script_component.hpp"

/*
Acoustic propagation kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It propagates a list of sound events to one listener as a continuous level.
The level, not a hear/don't-hear flag, is the auditory stimulus.

Model, in order:
  - Spherical spreading.  A point source loses 20*log10(d) dB at range d, so
    the level falls 6 dB per doubling of distance.  SOURCED: the
    inverse-square law.  The 1 m floor keeps the source level at d = 0.
  - Air and weather absorption.  The engine of this term is AEE's published
    sound-propagation index aee_weather_currentSoundPropagation
    (0.3 to 2.0), computed by fnc_updateSoundPropagation from the temperature
    inversion, the wind, the rain, the foliage and the snow.  It scales the
    effective range: an index above 1 carries the sound further, below 1
    shorter.  The index is AEE's model, not a new constant.
  - Occlusion.  Each occluder position within the occlusion radius of the
    source-listener line of sight lowers the level by the occlusion loss.
    The caller collects a bounded occluder list with nearestTerrainObjects
    and lineIntersects; this kernel does the geometry.  UNSOURCED.

The event is [sourcePos ASL, sourceLevelDb, kind].  The kind is metadata: the
caller supplies the source level.  The result is a 0 to 1 stimulus per event,
the level mapped onto the hearing floor and the loud reference.

Constants: the 6 dB per doubling is SOURCED.  The occlusion loss and radius,
the hearing floor and the loud reference are UNSOURCED modelling choices.

Arguments:
  0: Array  - events, each [sourcePos ASL, sourceLevelDb, kind]
  1: Array  - the listener position, ASL
  2: Number - the propagation index, 0.3 to 2.0
  3: Array  - occluder positions, ASL
  4: Number - the occlusion loss per occluder, dB
  5: Number - the occlusion radius, metres
  6: Number - the hearing floor, dB
  7: Number - the loud reference, dB

Returns:
  Array - one [kind, stimulus] row per event, stimulus 0 to 1
*/

params [
    ["_events", [], [[]]],
    ["_listenerPos", [0, 0, 0], [[]]],
    ["_propagationIndex", 1, [0]],
    ["_occluders", [], [[]]],
    ["_occlusionDb", WILDLIFE_ACOUSTIC_OCCLUSION_DB, [0]],
    ["_occlusionRadiusM", WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M, [0]],
    ["_hearingFloorDb", WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB, [0]],
    ["_loudDb", WILDLIFE_ACOUSTIC_LOUD_DB, [0]]
];

private _index = ((_propagationIndex max 0.3) min 2.0);
private _span = (_loudDb - _hearingFloorDb);
if (_span <= 0) then { _span = 1; };

private _out = [];
for "_i" from 0 to ((count _events) - 1) do {
    private _event = _events select _i;
    if ((_event isEqualType []) && ((count _event) >= 3)) then {
        private _source = _event select 0;
        private _sourceDb = _event select 1;
        private _kind = _event select 2;

        // Spherical spreading.  The propagation index scales the effective
        // range, so the weather enters the same distance term.
        private _dx = (_listenerPos select 0) - (_source select 0);
        private _dy = (_listenerPos select 1) - (_source select 1);
        private _dz = 0;
        if (((count _listenerPos) >= 3) && ((count _source) >= 3)) then {
            _dz = (_listenerPos select 2) - (_source select 2);
        };
        private _distance = sqrt ((_dx * _dx) + (_dy * _dy) + (_dz * _dz));
        private _effective = _distance / _index;
        private _spreadDb = 20 * (log (_effective max 1));

        // Occlusion: each occluder near the source-listener line lowers the
        // level.  The closest approach of the occluder to the segment is the
        // line-of-sight test.
        private _blocked = 0;
        for "_o" from 0 to ((count _occluders) - 1) do {
            private _occluder = _occluders select _o;
            if ((_occluder isEqualType []) && ((count _occluder) >= 2)) then {
                private _ax = _source select 0;
                private _ay = _source select 1;
                private _az = 0;
                private _bx = _listenerPos select 0;
                private _by = _listenerPos select 1;
                private _bz = 0;
                if (((count _source) >= 3) && ((count _listenerPos) >= 3)) then {
                    _az = _source select 2;
                    _bz = _listenerPos select 2;
                };
                private _abx = _bx - _ax;
                private _aby = _by - _ay;
                private _abz = _bz - _az;
                private _lenSq = (_abx * _abx) + (_aby * _aby) + (_abz * _abz);
                private _t = 0;
                if (_lenSq > 0) then {
                    _t = ((((_occluder select 0) - _ax) * _abx)
                        + (((_occluder select 1) - _ay) * _aby)
                        + (((_occluder select 2) - _az) * _abz)) / _lenSq;
                    _t = (_t max 0) min 1;
                };
                private _cx = _ax + (_t * _abx);
                private _cy = _ay + (_t * _aby);
                private _cz = _az + (_t * _abz);
                private _ox = (_occluder select 0) - _cx;
                private _oy = (_occluder select 1) - _cy;
                private _oz = (_occluder select 2) - _cz;
                private _closest = sqrt ((_ox * _ox) + (_oy * _oy) + (_oz * _oz));
                if (_closest <= _occlusionRadiusM) then { _blocked = _blocked + 1; };
            };
        };

        private _levelDb = _sourceDb - _spreadDb - (_blocked * _occlusionDb);
        private _stimulus = (((_levelDb - _hearingFloorDb) / _span) max 0) min 1;
        _out pushBack [_kind, _stimulus];
    };
};

_out
