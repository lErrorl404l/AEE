#include "..\script_component.hpp"
/*
Vehicle armour database (issue #168).

Resolves the REAL protection of a vehicle from its CfgVehicles classname
and returns [stanagLevel, rhaEquivalentMm, defeats]:

  stanagLevel     - the STANAG 4569 Ed 2 protection level (1..6)
  rhaEquivalentMm - the equivalent rolled-homogeneous-armour thickness
  defeats         - the weapon class the armour defeats:
                      "7.62AP" / "14.5mm" / "20mm" / "25mm" / "30mm" /
                      "120mmKE"

The STANAG 4569 Ed 2 ladder (the researched mapping):
  Level 1: 5.56/7.62 ball + 0.5 kg blast
  Level 2: 7.62x39 API + 6 kg blast
  Level 3: 7.62x54R AP (B32) + 8 kg blast
  Level 4: 14.5x114 AP (B32) + 10 kg blast
  Level 5: 25mm APDS + 25 kg blast
  Level 6: 30mm APFSDS + underbelly blast

The database is DYNAMIC: the vanilla vehicle classname's family signal
(B_MRAP, B_APC_Wheeled, O_MBT, B_APC_Tracked ...) keys the real analogue
(MRAP -> Cougar/JLTV L2-3, IFV -> Bradley L4-5, MBT -> Abrams/Leopard 2
L6).  A vehicle AEE has never seen falls back to its class's armour
ladder (the #126 config) with a documented "unverified" flag.

Arguments:
  0: vehicle (OBJECT, default the player's vehicle)

Returns [stanagLevel, rhaEquivalentMm, defeats].
*/
params [["_vehicle", vehicle player, [objNull]]];
if (isNull _vehicle) exitWith { [0, 0, "none"] };

private _v = toLower (typeOf _vehicle);

// The family -> real analogue -> STANAG level.  RHA-equivalent and the
// defeating weapon class from the researched table (issue #168 sources:
// vehicle brochures, Janes, army manuals, the ABE ir_armor seed).
switch (true) do {
    // ── Wheeled light (unarmoured / soft-skin) ──
    case (_v find "offroad" >= 0 ||
          _v find "hatchback" >= 0 ||
          _v find "quadbike" >= 0 ||
          _v find "van" >= 0):                 { [0, 5, "7.62ball"] };
    // ── Trucks (soft-skin, no protection) ──
    case (_v find "truck" >= 0 ||
          _v find "hemtt" >= 0 ||
          _v find "zamak" >= 0 ||
          _v find "kamaz" >= 0):               { [0, 5, "7.62ball"] };
    // ── Protected patrol (JLTV/HMMWV up-armoured, L2) ──
    case (_v find "lsv" >= 0 ||
          _v find "mrap" >= 0 ||
          _v find "offroad_" >= 0):            { [2, 20, "7.62API"] };
    // ── Wheeled APC (Stryker/BTR-82A/AMV, L4) ──
    case (_v find "apc_wheeled" >= 0 ||
          _v find "amv" >= 0 ||
          _v find "btr" >= 0):                 { [4, 60, "14.5mm"] };
    // ── Tracked APC (M113/MT-LB, L2-3) ──
    case (_v find "apc_tracked" >= 0 ||
          _v find "mtlb" >= 0):                { [3, 40, "7.62AP"] };
    // ── IFV (Bradley/BMP-3/CV90, L5) ──
    case (_v find "ifv" >= 0 ||
          _v find "bmp" >= 0 ||
          _v find "bradley" >= 0 ||
          _v find "cv90" >= 0):                { [5, 120, "25mm"] };
    // ── SPAAG (Linebacker/Gepard, L4-5) ──
    case (_v find "_aa" >= 0 ||
          _v find "aa_" >= 0 ||
          _v find "gepard" >= 0 ||
          _v find "shilka" >= 0):              { [5, 100, "25mm"] };
    // ── MBT (Abrams/Leopard 2/T-90, L6) ──
    case (_v find "mbt" >= 0 ||
          _v find "tank" >= 0 ||
          _v find "abrams" >= 0 ||
          _v find "leopard" >= 0 ||
          _v find "t72" >= 0 ||
          _v find "t80" >= 0 ||
          _v find "t90" >= 0 ||
          _v find "challenger" >= 0 ||
          _v find "armata" >= 0):              { [6, 650, "120mmKE"] };
    // ── Artillery / SAM (crew protection only, L3-4) ──
    case (_v find "artillery" >= 0 ||
          _v find "mlrs" >= 0 ||
          _v find "sam" >= 0 ||
          _v find "pzh" >= 0 ||
          _v find "m109" >= 0):                { [4, 50, "14.5mm"] };
    // ── Default: unresolved class - the penetration gate falls back to
    //    the armour-pool ladder (the #126 config).  Returning 0 RHA
    //    signals "not in the database", not "no protection".
    default                                     { [0, 0, "none"] };
};