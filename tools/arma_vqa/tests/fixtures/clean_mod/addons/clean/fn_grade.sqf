// Everything here is used the documented way. The whole file must produce no warnings or errors.
private _cc = ppEffectCreate ["ColorCorrections", 1500];
if (_cc < 0) exitWith {};
_cc ppEffectEnable true;
_cc ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 0.8], [0.299, 0.587, 0.114, 0]];
_cc ppEffectCommit 2;
sleep 2;
_cc ppEffectEnable false;
ppEffectDestroy _cc;

// thermal window left at its defaults, and re-applied after a savegame load
setTIParameter ["OutputRangeStart", 0.1];
addMissionEventHandler ["Loaded", {
    setTIParameter ["OutputRangeStart", 0.1];
    setTIParameter ["OutputRangeWidth", 0.8];
}];

// camera with a commit
private _cam = "camera" camCreate [0, 0, 0];
_cam cameraEffect ["Internal", "BACK"];
_cam camSetFov 0.75;
_cam camCommit 0;
true setCamUseTI 1;
camUseNVG false;
setAperture -1;
