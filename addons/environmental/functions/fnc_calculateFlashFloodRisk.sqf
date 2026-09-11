#include "..\script_component.hpp"

/*
Flash-flood risk index (0–1) after heavy rain, especially in arid terrain.

Arid soils have low infiltration — even modest rain can produce runoff.
Non-arid terrain needs a higher rain threshold to generate risk.

Risk decays by 50 % per tick so it recedes quickly once rain stops.

Stored in QGVAR(flashFloodRisk).
*/



private _rainAccum = missionNamespace getVariable [QGVAR(rainAccum), 0];
private _biome     = GVAR(biome);

// ─── Arid biomes — low infiltration, rapid runoff ──────────────────────────
private _isArid = false;
if (!isNil "_biome") then { _isArid = _biome in ["BWh","BWk","BSh","BSk"]; };

private _risk = 0;
if (_isArid) then {
    if (_rainAccum > 0.05) then {
        _risk = (_rainAccum - 0.05) * 4;
    };
} else {
    _risk = ((_rainAccum - 0.2) * 2) max 0;
};

// ─── 50 % decay per tick ───────────────────────────────────────────────────
_risk = _risk * 0.5;

_risk = _risk max 0 min 1;

missionNamespace setVariable [QGVAR(flashFloodRisk), _risk];

if (_risk > 0.6 && (GVAR(diagnostic))) then {
    diag_log text "[AEE] HIGH FLASH FLOOD RISK — reduce vehicle movement, monitor low-lying areas";
};

_risk
