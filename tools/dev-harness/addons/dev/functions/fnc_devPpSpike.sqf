/*
fnc_devPpSpike - engine post-process feasibility spike.

Runs once at client startup, before any mission. Waits for the renderer, then
runs five engine questions and writes one RPT line per question with the prefix
[AEE-PP-SPIKE]. It destroys every handle it creates.

The probe answers four engine questions:

  C1  DepthOfField is absent from the documented ppEffectCreate type list.
      Does the engine accept it?
  C2  Two creates at one priority. Does the second return -1, or a positive
      handle shared with the first?
  C3  ppEffectForceInNVG true, then adjust, commit, enable. Does the effect
      enable, and what is currentVisionMode? The thermal and NVG channels can
      only be reached through an optic, so this records normal vision only.
  C4  One effect adjusted, committed, then enabled. A second enabled, then
      adjusted, then committed. Compare ppEffectEnabled and ppEffectCommitted.

It also takes one screenshot (C5).

Client only. A dedicated server has no renderer. Call it through spawn so the
waits are scheduled.
*/

if (!hasInterface) exitWith {};
if (!isNil "aee_dev_pp_spike_done") exitWith {};
aee_dev_pp_spike_done = true;

// Wait for the renderer. The menu draws a few seconds after startup.
sleep 8;

private _tag = "[AEE-PP-SPIKE]";
private _line = "";
private _adjust = [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1], [0.299, 0.587, 0.114, 0]];

// C1: create DepthOfField at priority 868.
private _c1 = ppEffectCreate ["DepthOfField", 868];
_line = format ["%1 C1 DepthOfField-868 handle=%2", _tag, _c1];
diag_log _line;

// C2: create ColorCorrections twice at priority 1500.
private _c2a = ppEffectCreate ["ColorCorrections", 1500];
private _c2b = ppEffectCreate ["ColorCorrections", 1500];
private _c2aOn = if (_c2a < 0) then { "n/a" } else { str (ppEffectEnabled _c2a) };
private _c2bOn = if (_c2b < 0) then { "n/a" } else { str (ppEffectEnabled _c2b) };
_line = format [
    "%1 C2 dup-1500 first=%2 firstEnabled=%3 second=%4 secondEnabled=%5",
    _tag, _c2a, _c2aOn, _c2b, _c2bOn
];
diag_log _line;

// C3: force into NVG, adjust, commit, then enable.
private _c3 = ppEffectCreate ["ColorCorrections", 1501];
private _c3On = "n/a";
private _c3Vision = "n/a";
if (_c3 < 0) then {
    _line = format ["%1 C3 forceNVG handle=%2 reason=create-failed", _tag, _c3];
} else {
    _c3 ppEffectForceInNVG true;
    _c3 ppEffectAdjust _adjust;
    _c3 ppEffectCommit 0;
    sleep 1;
    _c3 ppEffectEnable true;
    sleep 1;
    _c3On = str (ppEffectEnabled _c3);
    if (!isNull player) then {
        _c3Vision = str (currentVisionMode player);
    } else {
        if (!isNull cameraOn) then {
            _c3Vision = str (currentVisionMode cameraOn);
        };
    };
    _line = format ["%1 C3 forceNVG handle=%2 enabled=%3 currentVisionMode=%4", _tag, _c3, _c3On, _c3Vision];
};
diag_log _line;

// Tell the renderer to drop the temporary NVG-forced effect before C4.
if (_c3 >= 0) then { _c3 ppEffectEnable false; };

// C4: two ordering paths.
private _c4a = ppEffectCreate ["ColorCorrections", 1502];
private _c4aOn = "n/a";
private _c4aCommitted = "n/a";
if (_c4a >= 0) then {
    _c4a ppEffectAdjust _adjust;
    _c4a ppEffectCommit 0;
    sleep 1;
    _c4a ppEffectEnable true;
    sleep 1;
    _c4aOn = str (ppEffectEnabled _c4a);
    _c4aCommitted = str (ppEffectCommitted _c4a);
};

private _c4b = ppEffectCreate ["ColorCorrections", 1503];
private _c4bOn = "n/a";
private _c4bCommitted = "n/a";
if (_c4b >= 0) then {
    _c4b ppEffectEnable true;
    sleep 1;
    _c4b ppEffectAdjust _adjust;
    _c4b ppEffectCommit 0;
    sleep 1;
    _c4bOn = str (ppEffectEnabled _c4b);
    _c4bCommitted = str (ppEffectCommitted _c4b);
};

_line = format [
    "%1 C4 adjust-commit-enable handle=%2 enabled=%3 committed=%4 enable-adjust-commit handle=%5 enabled=%6 committed=%7",
    _tag, _c4a, _c4aOn, _c4aCommitted, _c4b, _c4bOn, _c4bCommitted
];
diag_log _line;

// C5: screenshot. It returns Boolean and writes to <PROFILEDIR>\Screenshots.
private _shot = screenshot "aee_pp_spike";
_line = format ["%1 C5 screenshot-aee_pp_spike result=%2", _tag, _shot];
diag_log _line;

// Destroy every unique handle that was created.
private _handles = [];
{
    if ((_x >= 0) && {!(_x in _handles)}) then { _handles pushBack _x };
} forEach [_c1, _c2a, _c2b, _c3, _c4a, _c4b];

private _destroyed = [];
{
    ppEffectDestroy _x;
    _destroyed pushBack _x;
} forEach _handles;

_line = format ["%1 DESTROY handles=%2 destroyed=%3", _tag, _handles, _destroyed];
diag_log _line;
