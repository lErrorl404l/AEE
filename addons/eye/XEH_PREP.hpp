// XEH_PREP.hpp - function prep includes for aee_eye
//
// The eye adaptation model (issue #141): AEE owns the camera aperture and
// its rate.  Every kernel is PREP'd from functions/eye/; callers use FUNC.

PREPS(eye,eyeMesopicWeight);
PREPS(eye,eyePupilSteady);
PREPS(eye,eyePupilStep);
PREPS(eye,eyeAdaptStep);
PREPS(eye,eyeAdaptInit);
PREPS(eye,eyeAdaptState);
PREPS(eye,eyeTimeSkip);
PREPS(eye,eyeLimits);
PREPS(eye,eyeSceneLux);
PREPS(eye,eyeAmbientLux);
PREPS(eye,eyeLocalLux);
PREPS(eye,eyeSkyFraction);
PREPS(eye,eyeSkyCast);
PREPS(eye,eyeAperture);
PREPS(eye,eyeSampleScene);
PREPS(eye,eyeFlash);
PREPS(eye,eyeFlashScene);
PREPS(eye,updateEyeAdaptation);
PREPS(eye,initEyeAdaptation);
