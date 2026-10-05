// PHASE 83: the base-grade anchor and the default composed grade.
//
// The default normal-vision grade is the base game's neutral anchor [1, 1, 0]
// plus a small bounded improvement.  The client adjust path exits at
// hasInterface on a dedicated server, but the driver still reads the config
// anchor, resolves the debug override and publishes the resolved triple above
// that exit.  This probe drives the real driver and the real composition kernel
// headlessly and asserts the anchor, the override and the identity at default.

private _driver = missionNamespace getVariable ["aee_optics_fnc_applyBaseGrade", nil];
private _compose = missionNamespace getVariable ["aee_optics_fnc_perceptionParams", nil];
private _pass = 0;
private _fail = 0;
private _notes = [];

if (isNil "_driver" || isNil "_compose") then {
    _fail = _fail + 1;
    _notes pushBack "driver or composition kernel not compiled";
} else {
    // 1. The driver reads the loaded config once and caches [1, 1, 0].
    missionNamespace setVariable ["aee_optics_visionBaseAnchor", nil];
    [] call _driver;
    private _anchor = missionNamespace getVariable ["aee_optics_visionBaseAnchor", []];
    private _anchorOk = false;
    if (_anchor isEqualType []) then {
        if (_anchor isEqualTo [1, 1, 0]) then { _anchorOk = true; };
    };
    if (_anchorOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["anchor %1", str _anchor];
    };

    // 2. The debug hook overrides the resolved anchor, and clearing it returns
    //    to the vanilla anchor.
    missionNamespace setVariable ["aee_optics_visionForceBase", [1.1, 1.2, -0.05]];
    [] call _driver;
    private _forced = missionNamespace getVariable ["aee_optics_visionBaseResolved", []];
    private _forcedOk = false;
    if (_forced isEqualType []) then {
        if (_forced isEqualTo [1.1, 1.2, -0.05]) then { _forcedOk = true; };
    };
    if (_forcedOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["forced %1", str _forced];
    };
    missionNamespace setVariable ["aee_optics_visionForceBase", nil];
    [] call _driver;
    private _reset = missionNamespace getVariable ["aee_optics_visionBaseResolved", []];
    private _resetOk = false;
    if (_reset isEqualType []) then {
        if (_reset isEqualTo [1, 1, 0]) then { _resetOk = true; };
    };
    if (_resetOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["reset %1", str _reset];
    };

    // 3. The default composition has seven elements and the identity colour
    //    slots: no tint (colorize alpha 0) and the Rec.709 luma weights.
    private _params = [
        100,        // adapted luminance, cd/m2 (a photopic day)
        1,          // mesopic fraction 1, photopic
        [1, 1, 1],  // scene illuminant
        true,       // tone stage on
        false,      // white balance off (visionWhiteBalance default)
        0.25,       // tone strength (visionToneStrength default)
        1,          // contrast scale
        0.9,        // adaptation degree
        0,          // mesopic desaturation (visionMesopicDesaturation default)
        0,          // Purkinje strength (visionPurkinjeStrength default)
        [1, 1, 0],  // the vanilla anchor
        0           // bounded desaturation alpha at the defaults
    ] call _compose;
    private _cc = _params select 0;
    private _composeOk = false;
    if (_cc isEqualType []) then {
        if ((count _cc) isEqualTo 7) then {
            if ((_cc select 4) isEqualTo [1, 1, 1, 0]) then {
                if ((_cc select 5) isEqualTo [0.2126, 0.7152, 0.0722, 0]) then {
                    _composeOk = true;
                };
            };
        };
    };
    if (_composeOk) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["composed %1", str _cc];
    };
};

if (_fail isEqualTo 0) then {
    diag_log text format ["[P83] [PASS] base grade: anchor [1,1,0], debug override, identity composition (%1 checks)", _pass];
} else {
    diag_log text format ["[P83] [FAIL] base grade: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
