#include "..\script_component.hpp"

/*
ACE item classification (the ACE-bodied items).

The core equipment library holds no ACE convention.  ACE's kit carries its
own category: ACE marks a medical item with ACE_isMedicalItem, and the
category is what tells a medical item apart from unrelated gear whose
classname happens to share a word.  kat_IO_FAST is an intraosseous drill;
without a category it matched the helmet family "fast" and was weighed as
headgear.

The core asks the question and never reads an ACE field.  This compat
function answers it, so the knowledge stays in the ACE layer.

Argument:
  0: item (STRING, a classname, default "")

Returns true when the item is an ACE medical item.
*/

params [["_item", "", [""]]];
if (_item == "") exitWith { false };

private _cfg = configFile >> "CfgWeapons" >> _item;
if !(isClass _cfg) exitWith { false };

// ACE's own category tag, on the item class.
(getNumber (_cfg >> "ACE_isMedicalItem")) == 1
