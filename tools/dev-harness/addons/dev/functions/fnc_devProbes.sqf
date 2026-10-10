/*
fnc_devProbes - the console probe batch runner.

The console answers inside the ExtensionCallback on the extension's thread, so a
probe here must return on the calling thread.  A batch entry is a pure predicate
that reads the live merged config or a compiled kernel and returns
[passed, diag].  The tags are the mission probes' own [Pxx] tags and the file
each tag names is recorded in fnc_devProbeManifest, so a console fact keeps a
probe file behind it (tools/tests/test_console_fact_gating.py).

The runner honours the manifest class.  A "headless" probe runs on the calling
machine.  A "headless-client" probe runs only on a non-dedicated machine and an
"interface" probe only with an interface, so the runner reports
"client-unavailable" for either when the machine cannot carry it.  It never
reports a client probe as passing from a server-only run.

Batches: "headless".
*/
params [["_name", ""]];

private _members = switch (_name) do {
    case "headless": { ["P113", "P116", "P117", "P119", "P134"] };
    case "client": { ["P136"] };
    default { [] };
};
if ((count _members) == 0) exitWith { "error: unknown probe batch " + _name };

private _catalog = call aee_dev_fnc_devProbeManifest;

private _predicates = [
    ["P113", {
        private _notes = [];
        private _hill = getText (configFile >> "CfgLocationTypes" >> "Hill" >> "texture");
        if !(_hill isEqualTo "\z\aee\addons\cartography\data\terrain\hill.paa") then { _notes pushBack format ["Hill texture %1", _hill]; };
        private _fir = getText (configFile >> "CfgLocationTypes" >> "VegetationFir" >> "texture");
        if !(_fir isEqualTo "\z\aee\addons\cartography\data\terrain\coniferous.paa") then { _notes pushBack format ["VegetationFir texture %1", _fir]; };
        private _tx = getText (configFile >> "RscMapControl" >> "transmitter" >> "icon");
        if !(_tx isEqualTo "\z\aee\addons\cartography\data\terrain\radio_tower.paa") then { _notes pushBack format ["transmitter icon %1", _tx]; };
        private _sea = getArray (configFile >> "RscMapControl" >> "colorSea");
        if !(_sea isEqualTo [0.55, 0.7, 0.85, 1]) then { _notes pushBack format ["colorSea %1", _sea]; };
        private _alpha = getNumber (configFile >> "RscMapControl" >> "maxSatelliteAlpha");
        if !(_alpha > 0 && {_alpha < 1}) then { _notes pushBack format ["maxSatelliteAlpha %1", _alpha]; };
        private _font = getText (configFile >> "RscMapControl" >> "fontNames");
        if !(_font isEqualTo "RobotoCondensed") then { _notes pushBack format ["fontNames %1", _font]; };
        private _tables = missionNamespace getVariable ["aee_cartography_terrainTables", []];
        if !((count _tables) == 3 && {(count (_tables select 0)) > 0} && {(count (_tables select 1)) == 25} && {(count (_tables select 2)) == 26}) then { _notes pushBack format ["terrain tables %1", count _tables]; };
        private _cur = getText (configFile >> "CfgCurator" >> "DrawGroup" >> "textureUnknown");
        if !(_cur isEqualTo "\z\aee\addons\symbology\data\markers\AEE_u_unknown.paa") then { _notes pushBack format ["curator textureUnknown %1", _cur]; };
        [(count _notes) == 0, _notes joinString "; "]
    }],
    ["P116", {
        private _notes = [];
        private _mag = configFile >> "CfgMagazines";
        private _ammo = configFile >> "CfgAmmo";
        private _v556 = getNumber (_mag >> "30Rnd_556x45_Stanag" >> "initSpeed");
        if !(abs (_v556 - 914.4) <= 0.001) then { _notes pushBack format ["initSpeed 5.56=%1", _v556]; };
        private _v762 = getNumber (_mag >> "20Rnd_762x51_Mag" >> "initSpeed");
        if !(abs (_v762 - 838.2) <= 0.001) then { _notes pushBack format ["initSpeed 7.62=%1", _v762]; };
        private _magAmmo = getText (_mag >> "30Rnd_556x45_Stanag" >> "ammo");
        if !(_magAmmo == "B_556x45_Ball") then { _notes pushBack format ["mag ammo=%1", _magAmmo]; };
        private _a556 = getNumber (_ammo >> "B_556x45_Ball" >> "airFriction");
        if !(abs (_a556 - (-0.001175773)) <= 1e-7) then { _notes pushBack format ["airFriction 5.56=%1", _a556]; };
        private _a762 = getNumber (_ammo >> "B_762x51_Ball" >> "airFriction");
        if !(abs (_a762 - (-0.000929668)) <= 1e-7) then { _notes pushBack format ["airFriction 7.62=%1", _a762]; };
        private _caliber = getNumber (_ammo >> "B_556x45_Ball" >> "caliber");
        if !(_caliber > 0) then { _notes pushBack format ["caliber=%1", _caliber]; };
        [(count _notes) == 0, _notes joinString "; "]
    }],
    ["P117", {
        private _notes = [];
        {
            _x params ["_label", "_cfg"];
            private _numbers = getArray (_cfg >> "colorGrid");
            private _lines = getArray (_cfg >> "colorGridMap");
            private _ok = ((count _numbers) >= 4) && {(_numbers select 3) == 0} && {(count _lines) >= 4} && {(_lines select 3) == 0};
            if (!_ok) then { _notes pushBack format ["grid %1 colorGrid=%2 colorGridMap=%3", _label, str _numbers, str _lines]; };
        } forEach [
            ["RscMapControl", configFile >> "RscMapControl"],
            ["RscDisplayStrategicMap.Map", configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map"],
            ["ctrlMap", configFile >> "ctrlMap"]
        ];
        {
            private _icon = getText (configFile >> "CfgMarkers" >> _x >> "icon");
            if !((_icon find "z\aee\addons\symbology\data\markers") >= 0) then { _notes pushBack format ["engine marker %1 still vanilla: %2", _x, _icon]; };
        } forEach ["b_inf", "b_mech_inf", "o_naval", "n_installation", "c_car", "hd_dot", "hd_ambush", "mil_destroy", "mil_dot", "Contact_arrow1", "Contact_art1", "GroundSupport_CAS_WEST", "GroundSupport_ARTY_EAST", "group_0", "group_11", "respawn_inf", "waypoint"];
        [(count _notes) == 0, _notes joinString "; "]
    }],
    ["P119", {
        private _notes = [];
        private _scopes = [["b_inf", 1], ["b_armor", 1], ["b_unknown", 1], ["o_recon", 1], ["n_inf", 1], ["n_unknown", 1], ["hd_dot", 2], ["mil_marker", 1], ["waypoint", 1]];
        private _scopeBad = 0;
        {
            _x params ["_cls", "_min"];
            private _entry = configFile >> "CfgMarkers" >> _cls;
            if (isNull _entry || { (getNumber (_entry >> "scope")) < _min }) then { _scopeBad = _scopeBad + 1; };
        } forEach _scopes;
        if (_scopeBad > 0) then { _notes pushBack format ["scope bad=%1", _scopeBad]; };
        private _texBad = 0;
        {
            private _tex = getText (configFile >> "CfgMarkers" >> _x >> "texture");
            if ((_tex find "\z\aee\addons\symbology\data\markers\") < 0) then { _texBad = _texBad + 1; };
        } forEach ["b_inf", "o_armor", "n_recon", "hd_dot", "b_unknown"];
        if (_texBad > 0) then { _notes pushBack format ["texture bad=%1", _texBad]; };
        private _friendBad = 0;
        if !(isClass (configFile >> "CfgMarkerClasses" >> "AEE_Friend_Land")) then { _friendBad = _friendBad + 1; };
        {
            if !((getText (configFile >> "CfgMarkers" >> _x >> "markerClass")) isEqualTo "AEE_Friend_Land") then { _friendBad = _friendBad + 1; };
        } forEach ["AEE_b_inf", "AEE_b_armor", "AEE_b_hq"];
        if (_friendBad > 0) then { _notes pushBack format ["friend bad=%1", _friendBad]; };
        [(count _notes) == 0, _notes joinString "; "]
    }],
    ["P134", {
        private _notes = [];
        private _rsc = configFile >> "RscMapControl";
        private _vanilla = [
            ["ptsPerSquareSea", 5], ["ptsPerSquareTxt", 20], ["ptsPerSquareCLn", 10], ["ptsPerSquareExp", 10],
            ["ptsPerSquareCost", 10], ["ptsPerSquareFor", 9], ["ptsPerSquareForEdge", 9], ["ptsPerSquareRoad", 6], ["ptsPerSquareObj", 9]
        ];
        {
            _x params ["_key", "_want"];
            private _got = getNumber (_rsc >> _key);
            if (_got != _want) then { _notes pushBack format ["%1=%2 want %3", _key, _got, _want]; };
        } forEach _vanilla;
        {
            private _a = (getArray (_rsc >> _x)) param [3, -1];
            if (_a != 0) then { _notes pushBack format ["%1 alpha=%2 want 0", _x, _a]; };
        } forEach ["colorGrid", "colorGridMap"];
        [(count _notes) == 0, _notes joinString "; "]
    }],
    ["P136", {
        [!isDedicated, format ["non-dedicated machine, hasInterface=%1", hasInterface]]
    }]
];

private _rows = [];
{
    private _tag = _x;
    private _meta = _catalog select { (_x select 0) == _tag };
    if ((count _meta) == 0) then {
        _rows pushBack [_tag, "fail", "not in the probe manifest"];
    } else {
        private _class = (_meta select 0) select 1;
        private _file = (_meta select 0) select 2;
        private _canRun = switch (_class) do {
            case "headless-client": { !isDedicated };
            case "interface": { hasInterface };
            default { true };
        };
        if (!_canRun) then {
            _rows pushBack [_tag, "client-unavailable", format ["%1 needs class %2", _file, _class]];
        } else {
            private _pred = nil;
            {
                if ((_x select 0) == _tag) exitWith { _pred = _x select 1; };
            } forEach _predicates;
            if (isNil "_pred") then {
                _rows pushBack [_tag, "fail", format ["no console predicate for %1", _file]];
            } else {
                private _result = [] call _pred;
                private _ok = _result param [0, false];
                private _diag = _result param [1, ""];
                _rows pushBack [_tag, (if (_ok) then { "pass" } else { "fail" }), _diag];
            };
        };
    };
} forEach _members;

_rows
