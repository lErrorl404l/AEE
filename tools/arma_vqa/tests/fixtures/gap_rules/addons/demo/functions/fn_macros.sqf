// CBA/ACE style GVAR() handles must be tracked like any other variable.
// This block is correct: expect NO PP007/PP008/PP009 for it.
GVAR(ppe) = ppEffectCreate ["ColorCorrections", 1600];
GVAR(ppe) ppEffectEnable true;
GVAR(ppe) ppEffectForceInNVG true;
GVAR(ppe) ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1], [0.299, 0.587, 0.114, 0], [10, 10, 0, 0, 0, 0.1, 0.5]];
GVAR(ppe) ppEffectCommit 0.4;

// A helper that returns its handle: the caller enables / destroys it, so no lifecycle noise here.
private _make = {
    params ["_type", "_prio"];
    private _h = ppEffectCreate [_type, _prio];
    _h ppEffectAdjust [1];
    _h
};

// Broken on purpose, through GVAR(): wrong array length, never enabled, never committed.
GVAR(bad) = ppEffectCreate ["ColorCorrections", 1700];
GVAR(bad) ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1]];
