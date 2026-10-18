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
    (0.3 to 2.0), computed by fnc_updateSoundPropagation from ISO 9613 (air
    absorption, ground, foliage) and the ambient noise floor.  It scales the
    effective range: an index above 1 carries the sound further, below 1
    shorter.  The index is AEE's model, not a new constant.
  - Barriers.  A building, wall or fence between source and listener whose
    top stands above the line of sight diffracts the sound: ISO 9613-2
    eq. 14, D_z = 10 log10(3 + (20/lambda) z) at 500 Hz, z the path
    difference over the top, capped at 20 dB (clause 7.4); the worst barrier
    governs.  The caller collects the barriers (fnc_acousticOccluders).

The event is [sourcePos ASL, sourceLevelDb, kind].  The result is a 0 to 1
stimulus per event: the level above the hearing floor (the published ambient
noise floor, which masks quieter sounds) over the span to the loud reference,
140 dB peak, the level WHO's Guidelines for Community Noise (1999, s.4.2.6)
say adults should never be exposed to.

Arguments:
  0: Array  - events, each [sourcePos ASL, sourceLevelDb, kind]
  1: Array  - the listener position, ASL
  2: Number - the propagation index, 0.3 to 2.0
  3: Array  - barriers [x, y, topASL, halfWidth]
  4: Number - the barrier cap, dB (ISO 9613-2: 20)
  5: Number - the fallback barrier half-width, metres
  6: Number - the hearing floor (ambient noise), dB
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

        // Barriers: ISO 9613-2 eq. 14 single diffraction at 500 Hz,
        // D_z = 10 log10(3 + (20 / lambda) z), lambda = 343/500 m, capped at
        // 20 dB (clause 7.4); z the path difference over the barrier top.
        // The worst barrier governs.
        private _ax = _source select 0;
        private _ay = _source select 1;
        private _az = _source param [2, 0];
        private _bx = _listenerPos select 0;
        private _by = _listenerPos select 1;
        private _bz = _listenerPos param [2, 0];
        private _abx = _bx - _ax;
        private _aby = _by - _ay;
        private _lenSq = (_abx * _abx) + (_aby * _aby);
        private _direct = sqrt (_lenSq + ((_bz - _az) ^ 2));
        private _barrierDb = 0;
        if (_lenSq > 1) then {
            {
                if ((_x isEqualType []) && {(count _x) >= 3}) then {
                    private _t = ((((_x select 0) - _ax) * _abx) + (((_x select 1) - _ay) * _aby)) / _lenSq;
                    if (_t > 0 && _t < 1) then {
                        private _cx = _ax + (_t * _abx);
                        private _cy = _ay + (_t * _aby);
                        private _off = [_x select 0, _x select 1] distance2D [_cx, _cy];
                        private _half = _x param [3, _occlusionRadiusM];
                        private _top = _x select 2;
                        private _los = _az + (_t * (_bz - _az));
                        if (_off <= _half && _top > _los) then {
                            private _d1 = sqrt (((_cx - _ax) ^ 2) + ((_cy - _ay) ^ 2) + ((_top - _az) ^ 2));
                            private _d2 = sqrt (((_bx - _cx) ^ 2) + ((_by - _cy) ^ 2) + ((_bz - _top) ^ 2));
                            private _z = (_d1 + _d2 - _direct) max 0;
                            private _dz = (10 * (log (3 + ((20 / (343 / 500)) * _z)))) min _occlusionDb;
                            _barrierDb = _barrierDb max _dz;
                        };
                    };
                };
            } forEach _occluders;
        };
        private _levelDb = _sourceDb - _spreadDb - _barrierDb;
        private _stimulus = (((_levelDb - _hearingFloorDb) / _span) max 0) min 1;
        _out pushBack [_kind, _stimulus];
    };
};

_out
