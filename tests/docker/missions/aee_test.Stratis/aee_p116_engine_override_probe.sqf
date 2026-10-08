// PHASE 116: engine override programme, headless.
//
// Proves the generated overrides loaded from the PBO and that restating the
// parent kept the vanilla inheritance (ADR-001). Reads the engine config
// directly:
//   * CfgMagazines initSpeed on a 5.56 and a 7.62 magazine (real service
//     muzzle velocity);
//   * CfgAmmo airFriction on two ball rounds (derived from the held ballistic
//     coefficient and drag curve);
//   * the magazine ammo field and the projectile caliber survived the reopen,
//     which shows the class was not stripped by the reopen.
// It renders nothing.

private _pass = 0;
private _fail = 0;
private _notes = [];

private _mag = configFile >> "CfgMagazines";
private _ammo = configFile >> "CfgAmmo";

// initSpeed: 5.56 M855 service 914.4 m/s, 7.62 M80 service 838.2 m/s.
private _v556 = getNumber (_mag >> "30Rnd_556x45_Stanag" >> "initSpeed");
if (abs (_v556 - 914.4) <= 0.001) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["initSpeed 5.56=%1", _v556]; };

private _v762 = getNumber (_mag >> "20Rnd_762x51_Mag" >> "initSpeed");
if (abs (_v762 - 838.2) <= 0.001) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["initSpeed 7.62=%1", _v762]; };

// Inheritance kept: the magazine ammo field survived the reopen.
private _magAmmo = getText (_mag >> "30Rnd_556x45_Stanag" >> "ammo");
if (_magAmmo == "B_556x45_Ball") then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["mag ammo=%1", _magAmmo]; };

// airFriction: the derived values.
private _a556 = getNumber (_ammo >> "B_556x45_Ball" >> "airFriction");
if (abs (_a556 - (-0.001175773)) <= 1e-7) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["airFriction 5.56=%1", _a556]; };

private _a762 = getNumber (_ammo >> "B_762x51_Ball" >> "airFriction");
if (abs (_a762 - (-0.000929668)) <= 1e-7) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["airFriction 7.62=%1", _a762]; };

// Inheritance kept: caliber is a BulletBase field and survived the reopen.
private _caliber = getNumber (_ammo >> "B_556x45_Ball" >> "caliber");
if (_caliber > 0) then { _pass = _pass + 1; } else { _fail = _fail + 1; _notes pushBack format ["caliber=%1", _caliber]; };

if ((_fail == 0) && {_pass >= 6}) then {
    diag_log text format ["[P116] [PASS] engine overrides: %1 checks", _pass];
} else {
    diag_log text format ["[P116] [FAIL] engine overrides: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
