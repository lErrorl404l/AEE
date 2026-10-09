/*
fnc_devVerbs - the console operation table.

The fixed set of operations the dispatcher accepts. An operation outside this
set is refused. No operation compiles agent input except `eval`, which the
four-layer gate already restricts to a dev host.
*/
[
    "ping",
    "get",
    "set",
    "dump",
    "eval",
    "callfunc",
    "batch",
    "scenario",
    "probes",
    "remote",
    "verbs"
]
