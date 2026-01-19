#ifndef _ofxCore_h_
#define _ofxCore_h_

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Status Codes */
#define kOfxStatOK 0
#define kOfxStatFailed 1
#define kOfxStatErrFatal 2
#define kOfxStatErrUnknown 3
#define kOfxStatErrMissingHostFeature 4
#define kOfxStatErrUnsupported 5
#define kOfxStatErrExists 6
#define kOfxStatErrFormat 7
#define kOfxStatErrMemory 8
#define kOfxStatErrBadHandle 9
#define kOfxStatErrBadIndex 10
#define kOfxStatErrValue 11
#define kOfxStatReplyYes 12
#define kOfxStatReplyNo 13
#define kOfxStatReplyDefault 14

typedef int OfxStatus;

/* Basic Types */
typedef struct OfxPropertySetStruct *OfxPropertySetHandle;
typedef struct OfxImageEffectStruct *OfxImageEffectHandle;
typedef struct OfxImageEffectByNameStruct *OfxImageEffectByNameHandle;
typedef struct OfxParamSetStruct *OfxParamSetHandle;
typedef struct OfxImageClipStruct *OfxImageClipHandle;
typedef struct OfxParamStruct *OfxParamHandle;
typedef void *OfxHandle;

/* Property Suite Definition */
typedef struct OfxPropertySuiteV1 {
  OfxStatus (*propSetPointer)(OfxPropertySetHandle properties, const char *property, int index, void *value);
  OfxStatus (*propSetString)(OfxPropertySetHandle properties, const char *property, int index, const char *value);
  OfxStatus (*propSetDouble)(OfxPropertySetHandle properties, const char *property, int index, double value);
  OfxStatus (*propSetInt)(OfxPropertySetHandle properties, const char *property, int index, int value);
  OfxStatus (*propSetPointerN)(OfxPropertySetHandle properties, const char *property, int count, void **value);
  OfxStatus (*propSetStringN)(OfxPropertySetHandle properties, const char *property, int count, const char **value);
  OfxStatus (*propSetDoubleN)(OfxPropertySetHandle properties, const char *property, int count, double *value);
  OfxStatus (*propSetIntN)(OfxPropertySetHandle properties, const char *property, int count, int *value);
  OfxStatus (*propGetPointer)(OfxPropertySetHandle properties, const char *property, int index, void **value);
  OfxStatus (*propGetString)(OfxPropertySetHandle properties, const char *property, int index, char **value);
  OfxStatus (*propGetDouble)(OfxPropertySetHandle properties, const char *property, int index, double *value);
  OfxStatus (*propGetInt)(OfxPropertySetHandle properties, const char *property, int index, int *value);
  OfxStatus (*propGetPointerN)(OfxPropertySetHandle properties, const char *property, int count, void **value);
  OfxStatus (*propGetStringN)(OfxPropertySetHandle properties, const char *property, int count, char **value);
  OfxStatus (*propGetDoubleN)(OfxPropertySetHandle properties, const char *property, int count, double *value);
  OfxStatus (*propGetIntN)(OfxPropertySetHandle properties, const char *property, int count, int *value);
  OfxStatus (*propReset)(OfxPropertySetHandle properties, const char *property);
  OfxStatus (*propGetDimension)(OfxPropertySetHandle properties, const char *property, int *count);
} OfxPropertySuiteV1;

/* Memory Suite Definition */
typedef struct OfxMemorySuiteV1 {
  OfxStatus (*memoryAlloc)(void *handle, size_t nBytes, void **allocatedData);
  OfxStatus (*memoryFree)(void *allocatedData);
} OfxMemorySuiteV1;

/* Host Struct */
typedef struct OfxHost {
  OfxPropertySetHandle host;
  void *(*fetchSuite)(OfxPropertySetHandle host, const char *suiteName, int suiteVersion);
} OfxHost;

/* Plugin Entry Points */
typedef struct OfxPlugin {
  const char *pluginApi;
  int apiVersion;
  const char *pluginIdentifier;
  unsigned int pluginVersionMajor;
  unsigned int pluginVersionMinor;
  void (*setHost)(OfxHost *host);
  OfxStatus (*mainEntry)(const char *action, const void *handle, OfxPropertySetHandle inArgs, OfxPropertySetHandle outArgs);
} OfxPlugin;

typedef int (*OfxGetNumberOfPluginsFunc)(void);
typedef OfxPlugin *(*OfxGetPluginFunc)(int nth);

#ifdef __cplusplus
}
#endif

#endif
