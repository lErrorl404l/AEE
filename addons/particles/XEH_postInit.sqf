#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ─── Refractive shock trace renderer (issue #217 follow-on) ──────────────
// Draws the bow-shock refractive contrast on the local player's own
// round.  Local-only, so the particle source the renderer attaches is
// always local and a dedicated server creates nothing.  The renderer
// re-reads the ballistics kernel each tick with the round's CURRENT
// velocity, so the trace fades as the round slows out of the supersonic
// regime instead of holding the muzzle value.
//
// THE ROUND COMES FROM THE SLOT THE OTHER FIRED HANDLERS IN THIS BUILD
// ALREADY READ, AND THE AMMUNITION IS FOUND BY CONTENT.
//
// A previous version took the round as the first OBJECT that was not the
// shooter, guarded by
//     _x isEqualType "OBJECT"
// That guard was wrong, and the live RPT at 13:59:54 on 29 Sep proved it:
// "isnull: Type String, expected Object" at this handler's line 92, four times
// in three seconds.  isEqualType compares the left value against the TYPE OF
// its right-hand argument, which is why this repository's own
// "isEqualType 0" and "isEqualType []" read correctly, their right-hand values
// being a Number and an Array.  The string literal "OBJECT" is therefore a
// String, so the guard really asked "is _x a String", it accepted the WEAPON
// CLASS at slot 1, and isNull then rejected that String.  The guard was also
// the same predicate as the ammunition scan below it, so the two branches
// could not have told a weapon class from an ammunition class apart.
//
// Slot 6 is the round, and the ballistics and optics fired handlers in this
// build already read it from there and both work in game.  A scan that cannot
// be proven is worse than the slot that is proven, so the round is taken from
// slot 6 and the scan is kept only where it adds real robustness.
//
// THE AMMUNITION IS STILL FOUND BY CONTENT, so it does not depend on any
// order.  The first element that names a CfgAmmo class is the ammunition.  A
// weapon class is a String too, and configFile >> CfgAmmo >> <weapon class> is
// not a class, so the config lookup is what separates the two.  A miss leaves
// it empty and the renderer falls back to a stated default calibre.
["Fired", {
    params ["_unit", "", "", "", "", "", "_projectile"];
    if (_unit isNotEqualTo (call CBA_fnc_currentUnit)) exitWith {};
    if (isNull _projectile) exitWith {};

    private _ammo = "";
    {
        if ((_ammo isEqualTo "") && (_x isEqualType "")) then {
            if (isClass (configFile >> "CfgAmmo" >> _x)) then { _ammo = _x };
        };
    } forEach _this;

    [_projectile, _ammo] call FUNC(renderSupersonicTrace);
}, QGVAR(supersonicTrace)] call EFUNC(lib,installPlayerEngineHandler);

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
