// XEH_PREP.hpp - function prep includes for aee_altitude
//
// Hypoxia, G-LOC, altitude DCS, barometric pressure and oxygen delivery.
// Split out of aee_physiology (ADR-032); oxygen/ carries the delivery model.

PREPS(altitude,calculateAltitudeAcclimatization);
PREPS(altitude,calculateAltitudeDCS);
PREPS(altitude,calculateBarometricPressure);
PREPS(altitude,calculateGLOC);
PREPS(altitude,calculateHypoxia);
PREPS(oxygen,calculateOxygenDelivery);
