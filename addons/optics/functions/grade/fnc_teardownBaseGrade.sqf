#include "..\..\script_component.hpp"

/*
Stop the base-grade PFH and release its two effects (image realism).

The handles come from the core registry owner records
aee_core_ppHandle_optics_BaseGrade / ..._BaseAcuity.  Those records are what
fnc_createPPEffect writes and fnc_destroyPPEffect resets.  The addon's own
legacy mirror is not written by the registry, so it must not be the source.

Neutralise the ColorCorrections and disable both handles BEFORE the registry
releases them, so a module disable leaves nothing live and no graded frame.
Every adjust and enable sits behind a >= 0 guard.

Arguments: none.

Returns:
  Nothing.
*/

if (!isNil QGVAR(baseGradePFH)) then {
    [GVAR(baseGradePFH)] call CBA_fnc_removePerFrameHandler;
    GVAR(baseGradePFH) = nil;
};

private _hCC = missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseGrade), -1];
private _hAcuity = missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseAcuity), -1];
if (_hCC >= 0) then {
    // Identity: the engine's own neutral post-process
    // (CfgPostProcessTemplates >> Default >> colorCorrections =
    // {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}}): colorize alpha 1, zero weights.
    _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]];
    _hCC ppEffectCommit 0;
    _hCC ppEffectEnable false;
};
if (_hAcuity >= 0) then {
    _hAcuity ppEffectEnable false;
};

["optics", "BaseGrade"] call EFUNC(core,destroyPPEffect);
["optics", "BaseAcuity"] call EFUNC(core,destroyPPEffect);
missionNamespace setVariable [QGVAR(baseGradeActive), false];

AEE_LOG_INFO("base grade torn down")
