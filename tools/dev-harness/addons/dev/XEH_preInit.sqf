// Compile the gate, its driver and the verb whitelist, and set the structural
// marker (Layer 1). No logging.
aee_dev_fnc_devGate = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devGate.sqf";
aee_dev_fnc_devGateLive = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devGateLive.sqf";
aee_dev_fnc_devVerbs = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devVerbs.sqf";
aee_dev_fnc_devFuncs = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devFuncs.sqf";
aee_dev_fnc_devDispatch = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devDispatch.sqf";
aee_dev_fnc_devExec = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devExec.sqf";
aee_dev_fnc_devRemote = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devRemote.sqf";
aee_dev_fnc_devClientReply = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devClientReply.sqf";
aee_dev_fnc_devReapplyVisual = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devReapplyVisual.sqf";
aee_dev_fnc_devScreenshot = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devScreenshot.sqf";
aee_dev_fnc_devDumpAll = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devDumpAll.sqf";
aee_dev_fnc_devOverlayToggle = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devOverlayToggle.sqf";
aee_dev_fnc_devProbeManifest = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devProbeManifest.sqf";
aee_dev_fnc_devProbes = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devProbes.sqf";
aee_dev_fnc_devClientProbe = compile preprocessFileLineNumbers "\z\aee\addons\dev\functions\fnc_devClientProbe.sqf";

aee_dev_present = true;
