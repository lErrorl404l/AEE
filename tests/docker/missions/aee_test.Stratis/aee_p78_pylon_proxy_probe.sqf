// PHASE 78: does a pylon proxy material join its parent engine material array?
//
// WHY THIS EXISTS. The thermal FPN material swap in
// fnc_applySelectionThermal.sqf:202-209 walks getObjectMaterials <vehicle> and
// calls setObjectMaterial [<index>, the FPN rvmat path] for EVERY slot whose
// current material is a non-empty string. The walk has NO name filter. If a
// pylon-mounted launcher's proxy material is one of those slots, the swap
// overwrites it and the launcher's own material (and its StageTI) is
// flattened. If the proxy keeps its own material, the engine thermal pass
// draws the launcher by itself.
//
// WHAT THIS MEASURES. The probe spawns a dynamic-loadout helicopter, records
// count getObjectMaterials and count getObjectTextures and both arrays
// VERBATIM, applies a launcher/missile pylon loadout, then records both again.
// It reports whether either count changed, whether any material path present
// after the loadout is absent before it, and whether any such new path is a
// launcher or proxy path. PASS means the measurement is DEFINITE, not that the
// answer is yes or no. The answer is the data.
//
// CAVEAT. The engine may not stream the pylon proxy model in the same frame as
// the loadout. A pylon that has not loaded may legitimately show no change, so
// the probe treats a no-change result as conclusive only after
// getPylonMagazines confirms the magazine is present. It does not claim to
// prove that an unloaded proxy would never join the array.
//
// ENGINE CALLS (Bohemia Interactive Community wiki, archived 2024-2025):
//   vehicle setPylonLoadout [pylon, magazine, forced, turret]
//     pylon: Number (index from 1) or String; turret [] equips to the pilot
//   getPylonMagazines vehicle -> Array of magazine class names
//   getAllPylonsInfo vehicle -> [index, name, turret, magazine, ammo, detail]
//   vehicle getCompatiblePylonMagazines pylon -> compatible magazine names
//   getObjectMaterials / getObjectTextures carry no hasInterface gate.
//
// Bounded and deterministic: a fixed candidate list, one loadout, two reads,
// one short sleep. Emits: [P78] [PASS] / [P78] [FAIL] <reason> lines.

private _candidates = [
    "B_Heli_Light_01_dynamicLoadout_F",
    "O_Heli_Light_02_dynamicLoadout_F",
    "I_Heli_light_03_dynamicLoadout_F",
    "B_Heli_Attack_01_dynamicLoadout_F",
    "O_Heli_Attack_02_dynamicLoadout_F"
];

private _heli = objNull;
private _pylonIdx = 0;
private _magazine = "";

// Pick the first airframe that spawns with pylons, and on it a compatible
// launcher or missile magazine. Prefer a missile/launcher; fall back to the
// first compatible magazine of any kind.
{
    if (!isNull _heli) exitWith {};
    private _cand = _x createVehicle [4700, 4700, 0];
    if (isNull _cand) then { continue; };
    // Let the airframe initialise its pylon config before the read.
    sleep 0.05;
    private _pinfo = getAllPylonsInfo _cand;
    if ((_pinfo isEqualType []) && {(count _pinfo) > 0}) then {
        private _pick = "";
        private _pickIdx = 0;
        private _last = "";
        private _lastIdx = 0;
        {
            _x params ["_idx", "_pname"];
            private _compat = _cand getCompatiblePylonMagazines _idx;
            if ((_compat isEqualType []) && {(count _compat) > 0} && {((_compat select 0) isEqualType "")}) then {
                {
                    private _lc = toLower _x;
                    if (_last == "") then { _last = _x; _lastIdx = _idx; };
                    if ((_pick == "") && {((_lc find "missile") >= 0) || {(_lc find "launcher") >= 0}}) then {
                        _pick = _x;
                        _pickIdx = _idx;
                    };
                } forEach _compat;
            };
        } forEach _pinfo;
        if ((_pick == "") && {_last != ""}) then { _pick = _last; _pickIdx = _lastIdx; };
        if (_pick != "") then {
            _heli = _cand;
            _pylonIdx = _pickIdx;
            _magazine = _pick;
        };
    };
    if (isNull _heli || {_heli != _cand}) then { deleteVehicle _cand; };
} forEach _candidates;

private _reason = "";
private _beforeMats = [];
private _beforeTexs = [];
private _afterMats = [];
private _afterTexs = [];
private _matChanged = false;
private _texChanged = false;
private _isLauncherPath = false;
private _conclusive = false;

if (isNull _heli) then {
    _reason = "no dynamic-loadout helicopter with pylons spawned";
} else {
    // Let the airframe settle before the baseline read, so engine start and
    // model stream are not part of the measured delta.
    _heli engineOn true;
    sleep 0.2;
    _beforeMats = getObjectMaterials _heli;
    _beforeTexs = getObjectTextures _heli;

    if (!(_beforeMats isEqualType []) || {!(_beforeTexs isEqualType [])}) then {
        _reason = "pre-loadout getObjectMaterials or getObjectTextures did not return an array";
    } else {
        diag_log text format ["[P78] DIAG heli=%1 pylons=%2 selectedPylon=%3 magazine=%4",
            typeOf _heli, count (getAllPylonsInfo _heli), _pylonIdx, _magazine];
        diag_log text format ["[P78] BEFORE materials(%1)=%2", count _beforeMats, _beforeMats];
        diag_log text format ["[P78] BEFORE textures(%1)=%2", count _beforeTexs, _beforeTexs];

        private _setOk = _heli setPylonLoadout [_pylonIdx, _magazine, false, []];
        if (!_setOk) then {
            diag_log text "[P78] DIAG setPylonLoadout forced=false returned false; retrying forced=true";
            _setOk = _heli setPylonLoadout [_pylonIdx, _magazine, true, []];
        };
        sleep 0.4;

        if (!_setOk) then {
            _reason = "setPylonLoadout returned false";
        } else {
            private _loaded = getPylonMagazines _heli;
            if (!(_loaded isEqualType []) || {!(_magazine in _loaded)}) then {
                _reason = format ["getPylonMagazines did not confirm the loaded magazine (loaded=%1)", _loaded];
            } else {
                _afterMats = getObjectMaterials _heli;
                _afterTexs = getObjectTextures _heli;
                if (!(_afterMats isEqualType []) || {!(_afterTexs isEqualType [])}) then {
                    _reason = "post-loadout getObjectMaterials or getObjectTextures did not return an array";
                } else {
                    _matChanged = (count _afterMats) != (count _beforeMats);
                    _texChanged = (count _afterTexs) != (count _beforeTexs);

                    private _newMats = [];
                    {
                        if ((_x isEqualType "") && {!(_x in _beforeMats)}) then { _newMats pushBack _x; };
                    } forEach _afterMats;

                    // Probe the target magazine's own config so the launcher/proxy
                    // test is grounded in the loaded object, not a guessed token.
                    private _magModel = getText (configFile >> "CfgMagazines" >> _magazine >> "model");
                    private _magMats = getArray (configFile >> "CfgMagazines" >> _magazine >> "hiddenSelectionsMaterials");
                    private _tokens = ["missile", "launcher", "pylon", "rocket", "pod"];
                    {
                        private _p = toLower _x;
                        private _hit = false;
                        {
                            if ((_x isEqualType "") && {_p == (toLower _x)}) then { _hit = true; };
                        } forEach _magMats;
                        if (!_hit) then {
                            { if ((_p find _x) >= 0) then { _hit = true; }; } forEach _tokens;
                        };
                        if (_hit) then { _isLauncherPath = true; };
                    } forEach _newMats;

                    diag_log text format ["[P78] AFTER materials(%1)=%2", count _afterMats, _afterMats];
                    diag_log text format ["[P78] AFTER textures(%1)=%2", count _afterTexs, _afterTexs];
                    diag_log text format ["[P78] DELTA materialCountChanged=%1 (materials %2->%3) textureCountChanged=%4 (textures %5->%6)",
                        _matChanged, count _beforeMats, count _afterMats, _texChanged, count _beforeTexs, count _afterTexs];
                    diag_log text format ["[P78] DELTA newMaterialPaths=%1", _newMats];
                    diag_log text format ["[P78] PROXY magazineModel=%1 magazineMaterials=%2 newPathIsLauncherProxy=%3",
                        _magModel, _magMats, _isLauncherPath];
                    _conclusive = true;
                };
            };
        };
    };
    if (!isNull _heli) then { deleteVehicle _heli; };
};

if (_conclusive) then {
    diag_log text format ["[P78] [PASS] conclusive: materials %1->%2 changed=%3; textures %4->%5 changed=%6; newLauncherProxyMaterialPath=%7; magazine=%8",
        count _beforeMats, count _afterMats, _matChanged, count _beforeTexs, count _afterTexs, _texChanged, _isLauncherPath, _magazine];
} else {
    diag_log text format ["[P78] [FAIL] %1", _reason];
};
