#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationFamilies
 *
 * Pure variation-family kernel.  Returns the generated variation-family table
 * aee_symbology_variationFamilies.  PURE: the table is loaded data, so the
 * kernel reads no marker, no unit, no setting and no world.
 *
 * Each family is [id, label, entry, markerClass, resolver, options].  Each
 * option is [id, label, source, values].  Each value is
 * [id, label, token, grade, source].  The first value of an option is its
 * family default.
 *
 * Return: <ARRAY> the family table.
 */
aee_symbology_variationFamilies
