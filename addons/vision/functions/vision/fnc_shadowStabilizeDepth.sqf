#include "..\..\script_component.hpp"

/*
Shadow depth and scene-state stabilization (aee-workshop-copy item 6, part 2).

Re-derived from fn_stabilizedepth.sqf in Adaptive Shadows (Workshop
3792830104).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.  The constants are
UNSOURCED: the change threshold 3 m, the entry/exit counts 2, the similar
threshold (changeThreshold * 2 max 8), the lower blend 0.60/0.40 and the
default decrease delay 0.3 s.

The kernel is PURE: no missionNamespace, no GVAR or EGVAR, no engine command.
The driver owns the state array and passes it back each tick.  The state array
is:
  [sceneState, entryCount, exitCount, stableDepth, stableScene,
   pendingScene, pendingSince, pendingDepth]

The scene state machine debounces ENTERING/ENCLOSED/LEAVING/OUTSIDE so a
single flickering classification does not toggle the protected state.  The
depth falls only after the scene and the depth agree for the decrease delay,
except in the enclosed fast-decrease path.

Arguments:
  0: Number  - raw classified depth in metres
  1: String  - scene from the classifier
  2: Number  - current time in seconds
  3: Number  - interior score from the classifier
  4: Number  - opening coverage from the classifier
  5: Number  - opening sensitivity, a percentage 3..50
  6: Number  - decrease delay in seconds
  7: Array   - state array above

Returns:
  [stableDepth, sceneState, fastDecrease, state]
*/

params [
    ["_rawDepth", 0, [0]],
    ["_scene", "NEAR", [""]],
    ["_now", 0, [0]],
    ["_interiorScore", 0, [0]],
    ["_openingCoverage", 0, [0]],
    ["_openingSensitivity", 12, [0]],
    ["_decreaseDelay", 0.3, [0]],
    ["_state", ["OUTSIDE", 0, 0, 0, "NEAR", "", -1, 0], [[]]]
];

private _sceneState = _state select 0;
private _entryCount = _state select 1;
private _exitCount = _state select 2;
private _stableDepth = _state select 3;
private _stableScene = _state select 4;
private _pendingScene = _state select 5;
private _pendingSince = _state select 6;
private _pendingDepth = _state select 7;

private _changeThreshold = 3;
private _sensitivity = (((_openingSensitivity / 100) max 0.03) min 0.50);
private _enclosedEvidence = _scene isEqualTo "INTERIOR" && _interiorScore >= 0.62 && _openingCoverage < _sensitivity;

// ─── Scene-state debounce ────────────────────────────────────────────────
if (_enclosedEvidence) then {
    _exitCount = 0;

    if (_sceneState isEqualTo "ENCLOSED") then {
        _entryCount = 2;
    } else {
        if (_sceneState isEqualTo "LEAVING") then {
            _sceneState = "ENCLOSED";
            _entryCount = 2;
        } else {
            if (_sceneState isEqualTo "ENTERING") then {
                _entryCount = _entryCount + 1;
            } else {
                _sceneState = "ENTERING";
                _entryCount = 1;
            };

            if (_entryCount >= 2) then {
                _sceneState = "ENCLOSED";
                _entryCount = 2;
            };
        };
    };
} else {
    _entryCount = 0;

    if (_sceneState isEqualTo "ENCLOSED") then {
        _sceneState = "LEAVING";
        _exitCount = 1;
    } else {
        if (_sceneState isEqualTo "LEAVING") then {
            _exitCount = _exitCount + 1;

            if (_exitCount >= 2) then {
                _sceneState = "OUTSIDE";
                _exitCount = 0;
            };
        } else {
            _sceneState = "OUTSIDE";
            _exitCount = 0;
        };
    };
};

private _fastDecrease = _sceneState isEqualTo "ENCLOSED" && _enclosedEvidence;

// ─── Depth stabilization ─────────────────────────────────────────────────
private _resultDepth = _stableDepth;

if (_rawDepth >= (_stableDepth - _changeThreshold)) then {
    if (_rawDepth > _stableDepth) then {
        _resultDepth = _rawDepth;
        _stableScene = _scene;
    };

    _pendingScene = "";
    _pendingSince = -1;
    _pendingDepth = _resultDepth;
} else {
    if (_sceneState isEqualTo "ENTERING") then {
        _pendingScene = "";
        _pendingSince = -1;
        _pendingDepth = _stableDepth;
    } else {
        if (_fastDecrease) then {
            _resultDepth = _rawDepth;
            _stableScene = _scene;
            _pendingScene = "";
            _pendingSince = -1;
            _pendingDepth = _rawDepth;
        } else {
            private _similarThreshold = (_changeThreshold * 2) max 8;

            if (
                _scene isNotEqualTo _pendingScene
                || _pendingSince < 0
                || abs (_rawDepth - _pendingDepth) > _similarThreshold
            ) then {
                _pendingScene = _scene;
                _pendingSince = _now;
                _pendingDepth = _rawDepth;
            } else {
                _pendingDepth = (_pendingDepth * 0.60) + (_rawDepth * 0.40);
            };

            if (_decreaseDelay <= 0 || {_now - _pendingSince >= _decreaseDelay}) then {
                _resultDepth = _pendingDepth;
                _stableScene = _scene;
                _pendingScene = "";
                _pendingSince = -1;
            };
        };
    };
};

_stableDepth = _resultDepth;

[_stableDepth, _sceneState, _fastDecrease, [_sceneState, _entryCount, _exitCount, _stableDepth, _stableScene, _pendingScene, _pendingSince, _pendingDepth]]
