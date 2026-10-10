---
title: "AEE dev console contract"
---

# AEE dev console contract

The dev console is the SQF half of the native extension bridge (ADR-034,
ADR-035). The `aee_dev` extension registers a fixed command set; the console
accepts a fixed verb table; and the `callfunc` verb runs a function name only
when the name is on the `AEE_DEV_FUNCS` whitelist. This note is the contract.

Every list below is generated from its one source by
`tools/gen_dev_console_contract.py`. Do not edit it by hand. Run the generator
without `--check` to refresh it, and with `--check` to fail on drift, so a
source change that is not projected here cannot pass the gate.

<!-- BEGIN GENERATED: dev console contract -->

### Extension commands (16)

Registered by `init()` in `tools/dev-harness/extension/src/lib.rs`. SQF addresses one as `"aee_dev" callExtension "<name>"`.

- `__probe__`
- `kernel.calculateAirDensityKernel`
- `kernel.calculateBallisticDrag`
- `kernel.calculateRelativeHumidity`
- `kernel.calculateStationPressure`
- `kernel.eyeAdaptStep`
- `kernel.eyeMesopicWeight`
- `kernel.eyePupilSteady`
- `kernel.eyePupilStep`
- `kernel.eyeTimeSkip`
- `kernel.solveTwoNodeKernel`
- `ping`
- `reply`
- `reply_chunk`
- `start`
- `stop`

### Console verb table (12)

The operations `fnc_devExec.sqf` accepts, published as `aee_dev_verbs` by `fnc_devVerbs.sqf`. An operation outside the table is refused.

- `ping`
- `get`
- `set`
- `dump`
- `dumpall`
- `eval`
- `callfunc`
- `batch`
- `scenario`
- `probes`
- `remote`
- `verbs`

### Console function whitelist (`AEE_DEV_FUNCS`) (2)

The only function names the `callfunc` verb may run, published as `aee_dev_funcs` by `fnc_devFuncs.sqf`. A name outside the set is refused.

- `aee_diagnostics_fnc_dumpState`
- `aee_lib_fnc_readState`

<!-- END GENERATED: dev console contract -->
