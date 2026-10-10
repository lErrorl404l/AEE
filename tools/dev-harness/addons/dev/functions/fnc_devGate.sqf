/*
fnc_devGate

The four-layer dev trust gate. Returns true only when every layer holds. A
false layer leaves the dev channel a silent no-op: no per-frame handler, no
verb table, no log line.

Layer 1, structural: the dev addon is built and loaded. It is built by
tools/dev-harness/, outside the main addons/ tree, so a release cannot carry
it.
Layer 2, addon-load exclusion: the dev mod is not in the release mod list.
Layer 3, run-time: file patching is on, the sentinel file exists, and the
host is a dev host.
Layer 4, surface: the verb whitelist is fixed and no agent input is compiled.

Every input is a boolean. The driver (fnc_devGateLive) reads the engine
conditions and passes them, so this function is a pure kernel. A model that
touches the engine stays in the driver (ADR-034, the kernel split).
*/
params [
    ["_structural", false],
    ["_addonLoadOk", false],
    ["_filePatching", false],
    ["_sentinel", false],
    ["_devHost", false],
    ["_surfaceOk", false]
];

_structural && _addonLoadOk && _filePatching && _sentinel && _devHost && _surfaceOk
