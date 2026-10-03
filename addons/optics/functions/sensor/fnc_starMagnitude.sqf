#include "..\..\script_component.hpp"

/*
Apparent magnitude to render scale and brightness.

A star's visual magnitude is a logarithmic brightness scale: a difference
of 1 magnitude is a flux ratio of 10^-0.4 (~2.512x).  Brightness here is
therefore the Pogson flux relative to magnitude 0, clipped to [0, 1]:

    alpha = 10 ^ (-0.4 * vmag)

Sirius (vmag -1.46) pins at 1.0; a magnitude-6 star is ~0.4 % of that,
which is why the faintest stars fade out against the sky rather than
winking off.

Size is the one part of a star image that is NOT pure flux.  A point source
has no physical angular size, but a brighter star spreads into a larger
bloom (diffraction + atmospheric seeing).  The engine cannot model that
optics chain, so the issue anchors a declared curve: magnitude 0 is 1.5x
the apparent size of magnitude 2, linear between, clipped so the faint end
never collapses to a pixel:

    size = clamp(1.5 - 0.25 * vmag, 0.3, 1.5)

Arguments:
  0: Number - visual magnitude (smaller is brighter; Sirius is -1.46)

Returns:
  Array [sizeScale, alpha] - size multiplier and brightness in [0, 1].
*/

params [["_vmag", 0, [0]]];

private _alpha = ((10 ^ (-0.4 * _vmag)) max 0) min 1;
private _size = ((1.5 - 0.25 * _vmag) max 0.3) min 1.5;

[_size, _alpha]
