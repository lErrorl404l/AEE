// PHASE 143: the dynamic variation entry and the picker-collapse engine fact.
//
// The probe reads the merged config live and drives the pure variation
// kernels.  It proves what the collapse depends on:
//   (a) the one option-driven AEE_Variation entry is registered, picker-
//       visible and resolvable to a concrete APP-6 type;
//   (b) a concrete AEE variant places through setMarkerTypeLocal, and a
//       hidden-scope (scope = 0) CfgMarkers class still places the same way.
// It renders nothing and calls no engine draw command.  Emits one [P143]
// PASS/FAIL line.

private _fnResolve = missionNamespace getVariable ["aee_symbology_fnc_variationResolve", nil];
private _model = missionNamespace getVariable ["aee_symbology_variationFamilies", nil];
if (isNil "_fnResolve" || {isNil "_model"}) exitWith {
    diag_log text "[P143] [FAIL] variation kernels not compiled (variationResolve / variationFamilies)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the one option-driven entry is registered, picker-visible and textured
private _entry = configFile >> "CfgMarkers" >> "AEE_Variation";
private _entryScope = getNumber (_entry >> "scope");
private _entryTexture = getText (_entry >> "texture");
if (isClass _entry && {_entryScope > 0} && {_entryTexture isNotEqualTo ""}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["AEE_Variation scope=%1 texture=%2", _entryScope, _entryTexture];
};

// 2. the generated model loads and the resolver returns the concrete type
private _resolved = ["symbol", [["affiliation", "hostile"], ["function", "armour"]]] call _fnResolve;
if ((_resolved select 1) isEqualTo "AEE_o_armor") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["variationResolve hostile/armour=%1", _resolved];
};

// 3. a concrete AEE variant exists in the merged config
private _variant = configFile >> "CfgMarkers" >> "AEE_b_inf";
if (isClass _variant) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "AEE_b_inf is not registered";
};

// 4. a concrete AEE variant places through setMarkerTypeLocal
private _variantTexture = getText (_variant >> "texture");
private _marker = createMarkerLocal ["aee_p143_variant", [0, 0, 0]];
_marker setMarkerTypeLocal "AEE_b_inf";
if ((markerType _marker) isEqualTo "AEE_b_inf" && {_variantTexture isNotEqualTo ""}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["AEE_b_inf place readback=%1 texture=%2", markerType _marker, _variantTexture];
};
deleteMarkerLocal _marker;

// 5. a hidden-scope (scope = 0) CfgMarkers class still places through
//    setMarkerTypeLocal.  Prefer a scope-0 class that carries a texture (the
//    collapsed concrete variants); fall back to AEE_MarkerBase, the scope-0
//    building block, which proves script access to a hidden class.
private _aee = ("true" configClasses (configFile >> "CfgMarkers")) select {
    ((configName _x) select [0, 4]) isEqualTo "AEE_"
};
private _hidden = _aee select { getNumber (_x >> "scope") == 0 };
private _hiddenTextured = _hidden select { getText (_x >> "texture") isNotEqualTo "" };
private _subject = "";
if (_hiddenTextured isNotEqualTo []) then {
    _subject = configName (_hiddenTextured select 0);
} else {
    if (_hidden isNotEqualTo []) then {
        _subject = configName (_hidden select 0);
    };
};
if (_subject isNotEqualTo "") then {
    private _hiddenMarker = createMarkerLocal ["aee_p143_hidden", [0, 0, 0]];
    _hiddenMarker setMarkerTypeLocal _subject;
    private _hiddenTexture = getText (configFile >> "CfgMarkers" >> _subject >> "texture");
    private _ok = (markerType _hiddenMarker) isEqualTo _subject;
    if (_hiddenTextured isNotEqualTo []) then {
        _ok = _ok && {_hiddenTexture isNotEqualTo ""};
    } else {
        _notes pushBack format ["scope-0 subject %1 has no texture (pre-collapse); script access proven", _subject];
    };
    if (_ok) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["scope-0 %1 place readback=%2 texture=%3", _subject, markerType _hiddenMarker, _hiddenTexture];
    };
    deleteMarkerLocal _hiddenMarker;
} else {
    _fail = _fail + 1;
    _notes pushBack "no scope-0 AEE CfgMarkers class found";
};

// 6. the apply layer re-types a family marker from the active state, and the
//    restore reverts it to the family type.
private _fnApply = missionNamespace getVariable ["aee_symbology_fnc_variationApply", nil];
private _fnRestore = missionNamespace getVariable ["aee_symbology_fnc_symbologyMarkersRestore", nil];
if (!isNil "_fnApply" && {!isNil "_fnRestore"}) then {
    private _familyMarker = createMarkerLocal ["aee_p143_family", [0, 0, 0]];
    _familyMarker setMarkerTypeLocal "AEE_Variation";
    missionNamespace setVariable ["aee_symbology_variationState", [["affiliation", "hostile"], ["function", "armour"]]];
    [] call _fnApply;
    if ((markerType _familyMarker) isEqualTo "AEE_o_armor") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["variationApply -> %1", markerType _familyMarker];
    };
    missionNamespace setVariable ["aee_symbology_symbologyMarkerCache", [[_familyMarker, "AEE_Variation", "ColorAEE"]]];
    [] call _fnRestore;
    if ((markerType _familyMarker) isEqualTo "AEE_Variation") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["restore -> %1", markerType _familyMarker];
    };
    deleteMarkerLocal _familyMarker;
    missionNamespace setVariable ["aee_symbology_variationState", []];
} else {
    _fail = _fail + 1;
    _notes pushBack "variationApply / symbologyMarkersRestore not compiled";
};

// 7. the five variation settings are registered after init.
private _settingNames = [
    "aee_symbology_variationAffiliation", "aee_symbology_variationDimension",
    "aee_symbology_variationFunction", "aee_symbology_variationEchelon",
    "aee_symbology_variationPalette"
];
private _settingsOk = true;
{
    if (isNil { missionNamespace getVariable [_x, nil] }) then { _settingsOk = false; };
} forEach _settingNames;
if (_settingsOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "variation settings not registered";
};

// 8. the apply layer re-types a family marker for each of the five option states.
if (!isNil "_fnApply") then {
    private _switchMarker = createMarkerLocal ["aee_p143_switch", [0, 0, 0]];
    _switchMarker setMarkerTypeLocal "AEE_Variation";
    private _states = [
        [["affiliation", "hostile"], ["function", "armour"]],
        [["dimension", "air"], ["function", "fixed_wing"]],
        [["echelon", "company"]],
        [["palette", "OPFOR"]],
        [["function", "medical"]]
    ];
    private _switchOk = true;
    {
        _switchMarker setMarkerTypeLocal "AEE_Variation";
        missionNamespace setVariable ["aee_symbology_variationState", _x];
        [] call _fnApply;
        private _want = ["symbol", _x] call _fnResolve;
        if (!((markerType _switchMarker) isEqualTo (_want select 1))) then {
            _switchOk = false;
            _notes pushBack format ["switch state %1 -> %2 want %3", _x, markerType _switchMarker, _want select 1];
        };
    } forEach _states;
    if (_switchOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
    };
    deleteMarkerLocal _switchMarker;
    missionNamespace setVariable ["aee_symbology_variationState", []];
};

if (_fail == 0) then {
    diag_log text format ["[P143] [PASS] variation entry and marker placement (%1 checks)", _pass];
} else {
    diag_log text format ["[P143] [FAIL] variation entry: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
