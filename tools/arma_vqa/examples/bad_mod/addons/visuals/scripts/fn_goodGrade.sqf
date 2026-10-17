// Follows the wiki's recommended pattern; should produce no errors or warnings.
private _name = "ColorCorrections";
private _priority = 1500;
private _handle = -1;
while { _handle = ppEffectCreate [_name, _priority]; _handle < 0 } do { _priority = _priority + 1; };
_handle ppEffectEnable true;
_handle ppEffectAdjust [1, 1.1, 0, [0, 0, 0, 0], [1, 1, 1, 0.9], [0.299, 0.587, 0.114, 0]];
_handle ppEffectCommit 2;
waitUntil { ppEffectCommitted _handle };
uiSleep 3;
_handle ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 1], [0.299, 0.587, 0.114, 0]];
_handle ppEffectCommit 2;
uiSleep 2;
_handle ppEffectEnable false;
ppEffectDestroy _handle;
