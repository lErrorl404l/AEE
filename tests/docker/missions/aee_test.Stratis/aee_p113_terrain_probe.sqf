// PHASE 112: the terrain and map-feature config on the live world.
//
// The terrain layer is a load-time config re-declare, so the probe reads the
// MERGED config (configFile) and confirms the AEE values reached it: a
// location icon, an object icon, the sea fill colour and the satellite
// opacity.  It also confirms the terrain registry loaded at startup.  It
// renders nothing and draws no pixel.
//
// Emits one [P113] PASS/FAIL line.

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. the Hill location symbol is the AEE terrain texture
private _hill = getText (configFile >> "CfgLocationTypes" >> "Hill" >> "texture");
if (_hill isEqualTo "\z\aee\addons\optics\data\terrain\hill.paa") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["Hill texture unexpected: %1", _hill];
};

// 2. the VegetationFir location symbol is the AEE coniferous texture
private _fir = getText (configFile >> "CfgLocationTypes" >> "VegetationFir" >> "texture");
if (_fir isEqualTo "\z\aee\addons\optics\data\terrain\coniferous.paa") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["VegetationFir texture unexpected: %1", _fir];
};

// 3. the transmitter object icon is the AEE topographic texture
private _tx = getText (configFile >> "RscMapControl" >> "transmitter" >> "icon");
if (_tx isEqualTo "\z\aee\addons\optics\data\terrain\radio_tower.paa") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["transmitter icon unexpected: %1", _tx];
};

// 4. the sea fill is the standard water blue
private _sea = getArray (configFile >> "RscMapControl" >> "colorSea");
if (_sea isEqualTo [0.55, 0.7, 0.85, 1]) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["colorSea unexpected: %1", _sea];
};

// 5. the satellite opacity lever reached the config
private _alpha = getNumber (configFile >> "RscMapControl" >> "maxSatelliteAlpha");
if (_alpha > 0 && {_alpha < 1}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["maxSatelliteAlpha unexpected: %1", _alpha];
};

// 6. the map label font reached the config
private _font = getText (configFile >> "RscMapControl" >> "fontNames");
if (_font isEqualTo "AEEFont") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["fontNames unexpected: %1", _font];
};

// 7. the terrain registry loaded and names the three sections
private _tables = missionNamespace getVariable ["aee_optics_terrainTables", []];
if ((count _tables) == 3 && {(count (_tables select 0)) > 0}
    && {(count (_tables select 1)) == 25} && {(count (_tables select 2)) == 26}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["terrain registry unexpected: %1", count _tables];
};

// 8. Eden and Zeus carry the unknown-affiliation symbol, not the neutral one
private _curUnknown = getText (configFile >> "CfgCurator" >> "DrawGroup" >> "textureUnknown");
if (_curUnknown isEqualTo "\z\aee\addons\optics\data\markers\AEE_u_unknown.paa") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["curator textureUnknown unexpected: %1", _curUnknown];
};

if (_fail == 0) then {
    diag_log text format ["[P113] [PASS] terrain config on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P113] [FAIL] terrain config: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
