#include "..\..\script_component.hpp"
/*
 * Take a bounded batch from the pending thermal sweep queue.
 *
 * The ambient/ENTER discovery returns several hundred objects.  Solving them
 * all in one call was a single-frame hitch: the operator's run logged about
 * 700 objects and the per-selection solve measured about 1 ms each, so a full
 * pass cost roughly half a second in one frame.  The discovery now ENQUEUES
 * into a persistent pending list and each pass solves at most _budget of it.
 * A full sweep therefore spreads across ticks instead of stalling one.
 *
 * Nothing is dropped: an object stays queued until it is solved, and an
 * ambient change re-queues the whole discovered set because every object is
 * then dirty.  The remainder is returned so the caller can persist it.
 *
 * Pure: no engine call, so the headless probe can exercise it directly.
 *
 * Params:
 *   0: _pending (ARRAY)  - objects queued for the sweep
 *   1: _budget  (NUMBER, optional) - maximum objects returned this pass
 * Returns: [_batch (ARRAY), _remaining (ARRAY)]
 */
params [["_pending", [], [[]]], ["_budget", 16, [0]]];

private _n = count _pending;
// A zero or negative budget still makes progress: clamp to at least one.
private _take = (_budget max 1) min _n;
private _batch = _pending select [0, _take];
private _remaining = _pending select [_take, (_n - _take) max 0];

[_batch, _remaining]
