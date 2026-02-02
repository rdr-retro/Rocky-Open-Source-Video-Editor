#include "../../core/ofx/include/ofxImageEffect.h"
#include "../../core/ofx/include/ofxCore.h"
#include <cstring>
#include <algorithm>
#include <cmath>

#if defined(_WIN32)
  #define OFX_EXPORT __declspec(dllexport)
#else
  #define OFX_EXPORT __attribute__((visibility("default")))
#endif

// Plugin Identity
#define kPluginName "InvertColor"
#define kPluginGrouping "Color"
#define kPluginDescription "Inverts the colors of the image."
#define kPluginIdentifier "com.rocky.invert"
#define kPluginVersionMajor 1
#define kPluginVersionMinor 0

// Global Host Pointer
static OfxHost* gHost = nullptr;

// -----------------------------------------------------------------------------
// Action: Render
// -----------------------------------------------------------------------------
static OfxStatus render(OfxImageEffectHandle instance, OfxPropertySetHandle inArgs, OfxPropertySetHandle outArgs) {
    if (!gHost) return kOfxStatErrMissingHostFeature;

    // Extract buffers from arguments (provided by Host)
    void* src = nullptr;
    void* dst = nullptr;
    int width = 0;
    int height = 0;
    int rowBytes = 0;

    // Fetch Property Suite
    OfxPropertySuiteV1* propSuite = (OfxPropertySuiteV1*)gHost->fetchSuite(gHost->host, kOfxPropertySuite, 1);
    
    if (!propSuite) return kOfxStatErrMissingHostFeature;

    // In our simplified Host, we pass render args via the inArgs property set
    propSuite->propGetPointer(inArgs, "Rocky.SrcBuffer", 0, &src);
    propSuite->propGetPointer(inArgs, "Rocky.DstBuffer", 0, &dst);
    propSuite->propGetInt(inArgs, "Rocky.Width", 0, &width);
    propSuite->propGetInt(inArgs, "Rocky.Height", 0, &height);
    propSuite->propGetInt(inArgs, "Rocky.RowBytes", 0, &rowBytes);

    if (!src || !dst) return kOfxStatErrBadHandle;

    unsigned char* srcPtr = (unsigned char*)src;
    unsigned char* dstPtr = (unsigned char*)dst;

    // Optimized CPU Invert (RGBA 8-bit)
    // Uses 32-bit integer operations to invert RGB while preserving Alpha.
    // Mask: 0x00FFFFFF (Inverts R,G,B; Zero XOR for A preserves it) - Little Endian assumption
    
    // Check alignment for safety
    bool isAligned = (((uintptr_t)srcPtr % 4) == 0) && (((uintptr_t)dstPtr % 4) == 0) && ((rowBytes % 4) == 0);

    if (isAligned && rowBytes == width * 4) {
        // FAST PATH: Contiguous buffer, or at least 4-byte aligned rows
        // Treat as stream of uint32_t
        // If rowBytes == width * 4, we can even do one giant loop
        
        size_t totalPixels = (size_t)width * height;
        uint32_t* s32 = (uint32_t*)srcPtr;
        uint32_t* d32 = (uint32_t*)dstPtr;
        
        // This loop auto-vectorizes excellently on Clang (Mac M4) and MSVC (Windows)
        for (size_t i = 0; i < totalPixels; ++i) {
             d32[i] = s32[i] ^ 0x00FFFFFF;
        }
    } else {
        // SLOW PATH / ROW-BY-ROW SAFE PATH
        const uint32_t mask = 0x00FFFFFF;
        
        for (int y = 0; y < height; ++y) {
            // Process row as 32-bit integers if row pointers are aligned
            unsigned char* sRow = srcPtr + y * rowBytes;
            unsigned char* dRow = dstPtr + y * rowBytes;
            
            if (((uintptr_t)sRow % 4) == 0 && ((uintptr_t)dRow % 4) == 0) {
                 uint32_t* s32 = (uint32_t*)sRow;
                 uint32_t* d32 = (uint32_t*)dRow;
                 for (int x = 0; x < width; ++x) {
                     d32[x] = s32[x] ^ mask;
                 }
            } else {
                // FALLBACK: Byte-wise
                for (int x = 0; x < width; ++x) {
                    int idx = x * 4;
                    // R, G, B are inverted. Alpha is kept.
                    dRow[idx + 0] = 255 - sRow[idx + 0];
                    dRow[idx + 1] = 255 - sRow[idx + 1];
                    dRow[idx + 2] = 255 - sRow[idx + 2];
                    dRow[idx + 3] = sRow[idx + 3];
                }
            }
        }
    }

    return kOfxStatOK;
}

// -----------------------------------------------------------------------------
// Main Entry Point
// -----------------------------------------------------------------------------
OfxStatus userMainEntry(const char *action, const void *handle, OfxPropertySetHandle inArgs, OfxPropertySetHandle outArgs) {
    if (strcmp(action, kOfxActionLoad) == 0) {
        return kOfxStatOK;
    }
    if (strcmp(action, kOfxActionUnload) == 0) {
        return kOfxStatOK;
    }
    if (strcmp(action, kOfxActionDescribe) == 0) {
        return kOfxStatOK;
    }
    if (strcmp(action, kOfxImageEffectActionDescribeInContext) == 0) {
        return kOfxStatOK;
    }
    if (strcmp(action, kOfxImageEffectActionRender) == 0) {
        return render((OfxImageEffectHandle)handle, inArgs, outArgs);
    }
    
    return kOfxStatReplyDefault;
}

// -----------------------------------------------------------------------------
// Host Helper
// -----------------------------------------------------------------------------
static void setHost(OfxHost *host) {
    gHost = host;
}

// -----------------------------------------------------------------------------
// Factory / Exported Symbols
// -----------------------------------------------------------------------------
static OfxPlugin effectPlugin = {
    kOfxImageEffectPluginApi,
    1,
    kPluginIdentifier,
    1,
    0,
    setHost,
    userMainEntry
};

extern "C" {
    OFX_EXPORT int OfxGetNumberOfPlugins(void) {
        return 1;
    }

    OFX_EXPORT OfxPlugin* OfxGetPlugin(int nth) {
        if (nth == 0) return &effectPlugin;
        return nullptr;
    }
}
