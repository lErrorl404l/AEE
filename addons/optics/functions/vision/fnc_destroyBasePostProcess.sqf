#include "..\..\script_component.hpp"

/*
 * Release the persistent optics base post-process effects.
 *
 * These four (ChromAberration, DynamicBlur, ColorCorrections, FilmGrain) live
 * for the whole session and are adjusted, never created per tick.  Before the
 * shared registry they had no destroy path on any code path, so a stacked
 * second set from a repeat init stayed live for the rest of the session.
 *
 * Registered in the registry under the "optics" scope, so the whole set is
 * released in one call instead of repeating a name list by hand where a typo
 * would silently leak the rest.  Mirrored legacy names are reset to -1 by the
 * registry, so a reader holding one sees an invalid handle rather than a stale
 * positive number that fails every later call with "Invalid post process
 * handle".
 *
 * Returns: <NUMBER> how many handles were released.
 */
["optics", ""] call EFUNC(lib,destroyPPEffect)
