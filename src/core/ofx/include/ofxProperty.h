#ifndef _ofxProperty_h_
#define _ofxProperty_h_

#include "ofxCore.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Common Properties */
#define kOfxPropType "OfxPropType"
#define kOfxPropName "OfxPropName"
#define kOfxPropLabel "OfxPropLabel"
#define kOfxPropShortLabel "OfxPropShortLabel"
#define kOfxPropLongLabel "OfxPropLongLabel"
#define kOfxPropPluginDescription "OfxPropPluginDescription"
#define kOfxPropVersion "OfxPropVersion"
#define kOfxPropVersionLabel "OfxPropVersionLabel"

/* Image Effect Properties */
#define kOfxImageEffectPropSupportedContexts "OfxImageEffectPropSupportedContexts"
#define kOfxImageEffectPropGrouping "OfxImageEffectPropGrouping"
#define kOfxImageEffectPropRenderable "OfxImageEffectPropRenderable"
#define kOfxImageEffectPropSupportedPixelDepths "OfxImageEffectPropSupportedPixelDepths"
#define kOfxImageEffectPropSupportedComponents "OfxImageEffectPropSupportedComponents"

/* Types */
#define kOfxTypeImageEffect "OfxTypeImageEffect"
#define kOfxTypeImageEffectInstance "OfxTypeImageEffectInstance"
#define kOfxTypeImageEffectHost "OfxTypeImageEffectHost"
#define kOfxTypeClip "OfxTypeClip"
#define kOfxTypeParam "OfxTypeParam"

/* Contexts */
#define kOfxImageEffectContextFilter "OfxImageEffectContextFilter"
#define kOfxImageEffectContextGeneral "OfxImageEffectContextGeneral"

/* Pixel Depths */
#define kOfxBitDepthNone "OfxBitDepthNone"
#define kOfxBitDepthByte "OfxBitDepthByte"
#define kOfxBitDepthShort "OfxBitDepthShort"
#define kOfxBitDepthFloat "OfxBitDepthFloat"

/* Pixel Components */
#define kOfxImageComponentNone "OfxImageComponentNone"
#define kOfxImageComponentRGBA "OfxImageComponentRGBA"
#define kOfxImageComponentRGB "OfxImageComponentRGB"
#define kOfxImageComponentAlpha "OfxImageComponentAlpha"

#ifdef __cplusplus
}
#endif

#endif
