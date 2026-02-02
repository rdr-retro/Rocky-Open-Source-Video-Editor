#ifndef _ofxImageEffect_h_
#define _ofxImageEffect_h_

#include "ofxCore.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Actions */
#define kOfxActionLoad "OfxActionLoad"
#define kOfxActionUnload "OfxActionUnload"
#define kOfxActionDescribe "OfxActionDescribe"
#define kOfxActionCreateInstance "OfxActionCreateInstance"
#define kOfxActionDestroyInstance "OfxActionDestroyInstance"
#define kOfxImageEffectActionDescribeInContext "OfxImageEffectActionDescribeInContext"
#define kOfxImageEffectActionRender "OfxImageEffectActionRender"
#define kOfxImageEffectActionGetRegionOfDefinition "OfxImageEffectActionGetRegionOfDefinition"

#define kOfxImageEffectPluginApi "OfxImageEffectPluginAPI"

/* Suites */
#define kOfxPropertySuite "OfxPropertySuite"
#define kOfxImageEffectSuite "OfxImageEffectSuite"
#define kOfxParameterSuite "OfxParameterSuite"
#define kOfxMemorySuite "OfxMemorySuite"
#define kOfxMultiThreadSuite "OfxMultiThreadSuite"
#define kOfxMessageSuite "OfxMessageSuite"

/* Image Effect Suite V1 */
typedef struct OfxImageEffectSuiteV1 {
  OfxStatus (*getPropertySet)(OfxImageEffectHandle effect, OfxPropertySetHandle *propHandle);
  OfxStatus (*getParamSet)(OfxImageEffectHandle effect, OfxParamSetHandle *paramSetHandle);
  OfxStatus (*clipDefine)(OfxImageEffectHandle effect, const char *name, OfxPropertySetHandle *propertySet);
  OfxStatus (*clipGetHandle)(OfxImageEffectHandle effect, const char *name, OfxImageClipHandle *clip, OfxPropertySetHandle *propertySet);
  OfxStatus (*clipGetPropertySet)(OfxImageClipHandle clip, OfxPropertySetHandle *propHandle);
  OfxStatus (*clipGetImage)(OfxImageClipHandle clip, double time, const double *region, OfxPropertySetHandle *imageHandle);
  OfxStatus (*clipReleaseImage)(OfxPropertySetHandle imageHandle);
  OfxStatus (*clipGetRegionOfDefinition)(OfxImageClipHandle clip, double time, double *bounds);
  int (*abort)(OfxImageEffectHandle effect);
} OfxImageEffectSuiteV1;

#ifdef __cplusplus
}
#endif

#endif
