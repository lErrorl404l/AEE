/*
fnc_devFuncs - the AEE_DEV_FUNCS whitelist.

`callfunc` runs a function only when its name appears here. The set starts
small and is extended by a reviewed change. A name outside the set is refused
with an error, so the console cannot call arbitrary code.
*/
[
    "aee_core_fnc_dumpState",
    "aee_core_fnc_readState"
]
