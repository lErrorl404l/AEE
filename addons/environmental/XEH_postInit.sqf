#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ── Celestial renderers (issue #122) ──────────────────────────────────────
// Register the client-side starfield and meteor workers.  Both gate on the
// astronomy component's dynamicStars/dynamicMeteors settings and draw only
// local light emitters, so they run on the client.  Starfield first: the
// meteor renderer reuses the starfield's night and cloud state.
if (hasInterface) then {
    [] call FUNC(renderDynamicStars);
    [] call FUNC(renderMeteors);
    [] call FUNC(renderAurora);
    [] call FUNC(renderMilkyWay);
};
