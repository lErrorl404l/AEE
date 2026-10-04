// initSettings.inc.sqf - CBA Settings registration for aee_wildlife
//
// Included from XEH_preInit.sqf.  Titles and descriptions come from the
// wildlife stringtable.  Every category here is display metadata: the title
// key resolves with the ADDON prefix, so every key starts STR_AEE_Wildlife_.
//
// The ambient-sound ecology is client-local cosmetic ecology.  The fauna
// switch defaults false, so slice two stays inert until the operator opts in.

AEE_SETTING_CHECKBOX(enabled,"AEE Wildlife","General",true);

AEE_SETTING_SLIDER(tickInterval,"AEE Wildlife","General",0.5,2.0,1.0,0.1);

AEE_SETTING_CHECKBOX(ambientEnabled,"AEE Wildlife","Ambient Sound",true);

AEE_SETTING_CHECKBOX(animalsEnabled,"AEE Wildlife","Fauna",false);

AEE_SETTING_SLIDER(density,"AEE Wildlife","Fauna",0,2,1.0,0.05);

AEE_SETTING_SLIDER(maxAnimals,"AEE Wildlife","Fauna",0,32,16,1);

AEE_SETTING_SLIDER(spawnRadius,"AEE Wildlife","Fauna",100,800,350,10);

AEE_SETTING_SLIDER(despawnRadius,"AEE Wildlife","Fauna",200,1200,600,10);

AEE_SETTING_SLIDER(spookSensitivity,"AEE Wildlife","Behaviour",0,2,1.0,0.05);

AEE_SETTING_SLIDER(silenceDecay,"AEE Wildlife","Behaviour",0.01,0.2,0.05,0.005);

AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Wildlife",false);
