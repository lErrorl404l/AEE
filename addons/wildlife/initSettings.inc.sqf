// initSettings.inc.sqf - CBA Settings registration for aee_wildlife
//
// Included from XEH_preInit.sqf.  Titles and descriptions come from the
// wildlife stringtable.  Every category here is display metadata: the title
// key resolves with the ADDON prefix, so every key starts STR_AEE_Wildlife_.
//
// The ambient-sound ecology is client-local cosmetic ecology.  The fauna
// switch defaults false, so slice two stays inert until the operator opts in.
//
// The ecology layer is split into three subcategories.  Environment owns the
// neighbourhood grid sampler, Cognition owns the budgeted perceive-think-act
// tick, and Communication owns the heard-call bus.  Every numeric default
// mirrors the kernel default and the per-constant register.

AEE_SETTING_CHECKBOX(enabled,"AEE Wildlife","General",true);

AEE_SETTING_SLIDER(tickInterval,"AEE Wildlife","General",0.5,2.0,1.0,1);


AEE_SETTING_CHECKBOX(animalsEnabled,"AEE Wildlife","Fauna",false);

AEE_SETTING_SLIDER(density,"AEE Wildlife","Fauna",0,2,1.0,2);

AEE_SETTING_SLIDER(maxAnimals,"AEE Wildlife","Fauna",0,32,16,1);

AEE_SETTING_SLIDER(spawnRadius,"AEE Wildlife","Fauna",100,800,350,0);

AEE_SETTING_SLIDER(despawnRadius,"AEE Wildlife","Fauna",200,1200,600,0);

AEE_SETTING_SLIDER(spookSensitivity,"AEE Wildlife","Behaviour",0,2,1.0,2);


AEE_SETTING_SLIDER(hungerRate,"AEE Wildlife","Behaviour",0.001,0.1,0.02,3);

AEE_SETTING_SLIDER(thirstRate,"AEE Wildlife","Behaviour",0.001,0.2,0.03,3);

AEE_SETTING_SLIDER(herdSize,"AEE Wildlife","Behaviour",1,12,4,1);

AEE_SETTING_CHECKBOX(environmentEnabled,"AEE Wildlife","Environment",true);

AEE_SETTING_SLIDER(environmentCellSize,"AEE Wildlife","Environment",5,100,25,0);

AEE_SETTING_SLIDER(environmentBudgetMs,"AEE Wildlife","Environment",0,8,2.0,1);

AEE_SETTING_CHECKBOX(cognitionEnabled,"AEE Wildlife","Cognition",false);

AEE_SETTING_SLIDER(cognitionBudgetMs,"AEE Wildlife","Cognition",0,8,1.0,2);




AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Wildlife",false);
