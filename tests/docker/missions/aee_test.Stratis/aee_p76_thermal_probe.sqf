// PHASE 76: the thermal selection kernels, exercised on a headless server.
//
// WHY THIS EXISTS. The production thermal paint opens with
//     if (!hasInterface) exitWith { 0 };
// in every display function, and hasInterface is a read-only engine command.
// A dedicated server has hasInterface == false, so the paint path can never
// run here. Four kernels in that path carry no hasInterface gate and are
// reachable headlessly. This probe runs them directly.
//
// WHAT IS PROVEN HEADLESSLY (kernel return values):
//   (a) aee_thermal_fnc_getThermalSelections returns more than one selection
//       for a wheeled ground vehicle.
//   (b) aee_thermal_fnc_getThermalSelectionLag returns distinct values across
//       those selections.
//   (c) aee_thermal_fnc_thermalPalette returns different colours for those
//       lags.
//   (d) aee_mobility_fnc_getVehicleGeometry returns wheel_count > 0 for the
//       same vehicle. This is the runtime check for commit a2e2b4b, which the
//       RPT cannot show because the geometry kernel emits no log.
//
// The witness is a vehicle whose selections resolve to distinct model points.
// A vehicle whose selections all sit on the same point (for example a body
// camo set) returns one lag by design, so the probe walks a fixed candidate
// list and takes the first vehicle that shows the full per-selection spread.
// Selection indices are mapped to names two ways: the model selection names
// (what fnc_getThermalSelectionPoints resolves) and the config
// hiddenSelections names (what fnc_applyBuildingThermal passes for a vehicle).
//
// WHAT STILL NEEDS A CLIENT RUN (the rendered image): the paint line in
// fnc_applySelectionThermal running under a real player in currentVisionMode 2,
// and the engine thermal compositor showing the painted colours. A server has
// no camera and no display.
//
// Bounded: a fixed candidate list, one sleep, no unbounded wait. Deterministic.
// Emits: [P76] [PASS] / [P76] [FAIL] <reason> lines.

private _fnSel = missionNamespace getVariable ["aee_thermal_fnc_getThermalSelections", nil];
private _fnLag = missionNamespace getVariable ["aee_thermal_fnc_getThermalSelectionLag", nil];
private _fnPal = missionNamespace getVariable ["aee_thermal_fnc_thermalPalette", nil];
private _fnGeo = missionNamespace getVariable ["aee_mobility_fnc_getVehicleGeometry", nil];

if (isNil "_fnSel" || {isNil "_fnLag"} || {isNil "_fnPal"} || {isNil "_fnGeo"}) exitWith {
    diag_log text "[P76] [FAIL] kernel functions not compiled (selections/lag/palette/geometry)";
};

// Wheeled ground vehicles only. Fixed order, so the witness is reproducible.
private _candidates = [
    "B_APC_Wheeled_01_cannon_F",
    "I_APC_Wheeled_03_cannon_F",
    "O_APC_Wheeled_02_rcws_v2_F",
    "B_LSV_01_unarmed_F",
    "B_MRAP_01_F",
    "O_MRAP_02_F",
    "I_MRAP_03_F",
    "C_Offroad_01_F",
    "C_Hatchback_01_F",
    "C_SUV_01_F",
    "C_Van_01_transport_F",
    "C_Van_01_box_F",
    "B_Truck_01_transport_F",
    "B_Truck_01_box_F",
    "B_Truck_01_fuel_F",
    "O_Truck_02_transport_F",
    "O_Truck_03_transport_F",
    "I_Truck_02_transport_F",
    "B_Quadbike_01_F",
    "C_Kart_01_F",
    "C_Tractor_01_F",
    "B_G_Offroad_01_F",
    "B_G_Van_01_transport_F"
];

private _veh = objNull;
private _selIdx = [];
private _names = [];
private _lags = [];
private _geo = [];
private _mapping = "";

{
    if (!isNull _veh) exitWith {};
    private _cand = _x createVehicle [4400, 4400, 0];
    if (isNull _cand) then { continue; };
    private _wheeled = (_cand isKindOf "LandVehicle") && {!(_cand isKindOf "Tank")} && {!(_cand isKindOf "Tracked_APC")};
    private _s = if (_wheeled) then { [_cand] call _fnSel } else { [] };
    if ((_s isEqualType []) && {(count _s) > 1}) then {
        private _g = [_cand] call _fnGeo;
        // Two name mappings for the same selection indices.
        private _sn = selectionNames _cand;
        private _hs = getArray (configOf _cand >> "hiddenSelections");
        private _nModel = [];
        { if ((_x isEqualType 0) && {_x < count _sn}) then { _nModel pushBack (_sn select _x); }; } forEach _s;
        private _nHidden = [];
        { if ((_x isEqualType 0) && {_x < count _hs}) then { _nHidden pushBack (_hs select _x); }; } forEach _s;

        private _lModel = if ((count _nModel) > 1) then { [_cand, _nModel] call _fnLag } else { [] };
        if !(_lModel isEqualType []) then { _lModel = []; };
        private _lHidden = if ((count _nHidden) > 1) then { [_cand, _nHidden] call _fnLag } else { [] };
        if !(_lHidden isEqualType []) then { _lHidden = []; };
        private _uModel = _lModel arrayIntersect _lModel;
        private _uHidden = _lHidden arrayIntersect _lHidden;

        diag_log text format ["[P76] DIAG candidate=%1 sels=%2 wheels=%3 modelLags=%4 hiddenLags=%5",
            typeOf _cand, count _s, _g select 3, count _uModel, count _uHidden];

        if (((count _lModel) == (count _nModel)) && {(count _uModel) > 1} && {(_g select 3) > 0}) then {
            _veh = _cand;
            _selIdx = _s;
            _names = _nModel;
            _lags = _lModel;
            _geo = _g;
            _mapping = "model";
        } else {
            if (((count _lHidden) == (count _nHidden)) && {(count _uHidden) > 1} && {(_g select 3) > 0}) then {
                _veh = _cand;
                _selIdx = _s;
                _names = _nHidden;
                _lags = _lHidden;
                _geo = _g;
                _mapping = "hidden";
            };
        };
    };
    if (isNull _veh || {_veh != _cand}) then { deleteVehicle _cand; };
} forEach _candidates;

if (isNull _veh) exitWith {
    diag_log text "[P76] [FAIL] no wheeled ground vehicle among the candidates returned more than one selection with distinct lags and wheel_count > 0";
};

_veh engineOn true;
sleep 0.2;

private _lagUniq = _lags arrayIntersect _lags;

diag_log text format ["[P76] DIAG witness=%1 mapping=%2 selections=%3 names=%4 wheels=%5 source=%6",
    typeOf _veh, _mapping, count _selIdx, _names, _geo select 3, _geo select 4];

private _fail = 0;

// ── (a) more than one selection ───────────────────────────────────────────
if ((count _selIdx) > 1) then {
    diag_log text format ["[P76] [PASS] (a) getThermalSelections: %1 selections", count _selIdx];
} else {
    diag_log text format ["[P76] [FAIL] (a) getThermalSelections returned %1 selection, expected more than one", count _selIdx];
    _fail = _fail + 1;
};

// ── (b) distinct lags across those selections ─────────────────────────────
if (((count _lags) == (count _names)) && {(count _lagUniq) > 1}) then {
    diag_log text format ["[P76] [PASS] (b) getThermalSelectionLag: %1 distinct values over %2 selections", count _lagUniq, count _lags];
} else {
    diag_log text format ["[P76] [FAIL] (b) getThermalSelectionLag not distinct: lags=%1 names=%2", _lags, count _names];
    _fail = _fail + 1;
};

// ── (c) palette gives different colours for those lags ────────────────────
private _colours = [];
{
    private _rgb = [_x, 0, 0] call _fnPal;
    _colours pushBack (format ["%1,%2,%3", _rgb select 0, _rgb select 1, _rgb select 2]);
} forEach _lags;
private _colourUniq = _colours arrayIntersect _colours;
if ((count _colourUniq) > 1) then {
    diag_log text format ["[P76] [PASS] (c) thermalPalette: %1 colours over %2 lags", count _colourUniq, count _colours];
} else {
    diag_log text format ["[P76] [FAIL] (c) thermalPalette returned one colour for every lag: %1", _colours];
    _fail = _fail + 1;
};

// ── (d) wheel_count > 0 on a wheeled ground vehicle ───────────────────────
private _wheelCount = _geo select 3;
if (_wheelCount > 0) then {
    diag_log text format ["[P76] [PASS] (d) getVehicleGeometry: wheel_count=%1 (source=%2)", _wheelCount, _geo select 4];
} else {
    diag_log text format ["[P76] [FAIL] (d) getVehicleGeometry wheel_count=%1, expected > 0", _wheelCount];
    _fail = _fail + 1;
};

deleteVehicle _veh;

if (_fail == 0) then {
    diag_log text format ["[P76] [PASS] thermal selection kernels verified headlessly: %1 selections, %2 distinct lags, %3 distinct colours, wheel_count=%4",
        count _selIdx, count _lagUniq, count _colourUniq, _wheelCount];
} else {
    diag_log text format ["[P76] [FAIL] thermal selection kernels: %1 of 4 checks failed", _fail];
};
