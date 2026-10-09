/*
fnc_devVerbs - the fixed command whitelist (Layer 4).

No verb takes a code string. The dispatcher never compiles agent input, so a
dev session cannot become an arbitrary-code surface.
*/
[
    "ping",
    "gate",
    "get",
    "set",
    "call",
    "log",
    "time",
    "verbs",
    "stop"
]
