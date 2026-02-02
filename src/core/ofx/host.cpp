#include "host.h"
#include "include/ofxProperty.h"
#include <iostream>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <dlfcn.h>
#endif

#include <cstring>
#include <map>
#include <string>
#include <vector>

// -----------------------------------------------------------------------------
// Property Mechanism Implementation
// -----------------------------------------------------------------------------

struct RockyPropertySet {
    std::string name;
    std::map<std::string, std::string> strings;
    std::map<std::string, void*> pointers;
    std::map<std::string, int> ints;
    std::map<std::string, double> doubles;
};

// --- Property Suite V1 Callback Implementations ---

static OfxStatus propSetPointer(OfxPropertySetHandle properties, const char *property, int index, void *value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set) {
        set->pointers[property] = value;
        return kOfxStatOK;
    }
    return kOfxStatErrBadHandle;
}

static OfxStatus propGetPointer(OfxPropertySetHandle properties, const char *property, int index, void **value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set && set->pointers.find(property) != set->pointers.end()) {
        *value = set->pointers[property];
        return kOfxStatOK;
    }
    return kOfxStatErrValue;
}

static OfxStatus propSetString(OfxPropertySetHandle properties, const char *property, int index, const char *value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set) {
        set->strings[property] = std::string(value);
        return kOfxStatOK;
    }
    return kOfxStatErrBadHandle;
}

static OfxStatus propGetString(OfxPropertySetHandle properties, const char *property, int index, char **value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set && set->strings.find(property) != set->strings.end()) {
        // WARNING: internal string pointer return. Not thread safe or persistent if map reallocs.
        // For MVP this is acceptable.
        *value = (char*)set->strings[property].c_str();
        return kOfxStatOK;
    }
    return kOfxStatErrValue;
}

static OfxStatus propSetInt(OfxPropertySetHandle properties, const char *property, int index, int value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set) {
        set->ints[property] = value;
        return kOfxStatOK;
    }
    return kOfxStatErrBadHandle;
}

static OfxStatus propGetInt(OfxPropertySetHandle properties, const char *property, int index, int *value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set && set->ints.find(property) != set->ints.end()) {
        *value = set->ints[property];
        return kOfxStatOK;
    }
    return kOfxStatErrValue;
}

static OfxStatus propSetDouble(OfxPropertySetHandle properties, const char *property, int index, double value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set) {
        set->doubles[property] = value;
        return kOfxStatOK;
    }
    return kOfxStatErrBadHandle;
}

static OfxStatus propGetDouble(OfxPropertySetHandle properties, const char *property, int index, double *value) {
    RockyPropertySet* set = (RockyPropertySet*)properties;
    if (set && set->doubles.find(property) != set->doubles.end()) {
        *value = set->doubles[property];
        return kOfxStatOK;
    }
    return kOfxStatErrValue;
}

// Stubs for non-mvp functions (Array/Vector access)
static OfxStatus propSetPointerN(OfxPropertySetHandle properties, const char *property, int count, void **value) { return kOfxStatErrUnsupported; }
static OfxStatus propSetStringN(OfxPropertySetHandle properties, const char *property, int count, const char **value) { return kOfxStatErrUnsupported; }
static OfxStatus propSetDoubleN(OfxPropertySetHandle properties, const char *property, int count, double *value) { return kOfxStatErrUnsupported; }
static OfxStatus propSetIntN(OfxPropertySetHandle properties, const char *property, int count, int *value) { return kOfxStatErrUnsupported; }

static OfxStatus propGetPointerN(OfxPropertySetHandle properties, const char *property, int count, void **value) { return kOfxStatErrUnsupported; }
static OfxStatus propGetStringN(OfxPropertySetHandle properties, const char *property, int count, char **value) { return kOfxStatErrUnsupported; }
static OfxStatus propGetDoubleN(OfxPropertySetHandle properties, const char *property, int count, double *value) { return kOfxStatErrUnsupported; }
static OfxStatus propGetIntN(OfxPropertySetHandle properties, const char *property, int count, int *value) { return kOfxStatErrUnsupported; }

static OfxStatus propReset(OfxPropertySetHandle properties, const char *property) { return kOfxStatOK; }
static OfxStatus propGetDimension(OfxPropertySetHandle properties, const char *property, int *count) { *count = 1; return kOfxStatOK; }

static OfxPropertySuiteV1 gPropertySuite = {
    propSetPointer, 
    propSetString, 
    propSetDouble, 
    propSetInt, 
    propSetPointerN, 
    propSetStringN, 
    propSetDoubleN, 
    propSetIntN, 
    propGetPointer, 
    propGetString, 
    propGetDouble, 
    propGetInt, 
    propGetPointerN, 
    propGetStringN, 
    propGetDoubleN, 
    propGetIntN, 
    propReset, 
    propGetDimension
};

// -----------------------------------------------------------------------------
// Host Logic
// -----------------------------------------------------------------------------

RockyOfxHost& RockyOfxHost::getInstance() {
    static RockyOfxHost instance;
    return instance;
}

RockyOfxHost::RockyOfxHost() {
    ofxHostStruct = new OfxHost();
    
    // Create a global host property set
    hostProperties = new RockyPropertySet();
    hostProperties->name = "RockyHostProperties";
    hostProperties->strings[kOfxPropName] = "RockyVideoEditor";
    hostProperties->strings[kOfxPropLabel] = "Rocky";
    
    ofxHostStruct->host = (OfxPropertySetHandle)hostProperties;
    ofxHostStruct->fetchSuite = RockyOfxHost::fetchSuite;
}

RockyOfxHost::~RockyOfxHost() {
    shutdown();
    delete (RockyPropertySet*)ofxHostStruct->host;
    delete ofxHostStruct;
}

void RockyOfxHost::initialize() {
}

void* RockyOfxHost::fetchSuite(OfxPropertySetHandle host, const char* suiteName, int suiteVersion) {
    if (strcmp(suiteName, kOfxPropertySuite) == 0) {
        return &gPropertySuite;
    }
    return nullptr;
}

bool RockyOfxHost::loadPlugin(const std::string& path) {
    
    void* handle = nullptr;
    OfxGetNumberOfPluginsFunc getNumPlugs = nullptr;
    OfxGetPluginFunc getPlug = nullptr;

#ifdef _WIN32
    // Windows dynamic loading
    HMODULE hModule = LoadLibraryA(path.c_str());
    if (!hModule) {
        std::cerr << "[OFX] Failed to LoadLibrary: Error code " << GetLastError() << std::endl;
        return false;
    }
    handle = (void*)hModule;
    
    getNumPlugs = (OfxGetNumberOfPluginsFunc)GetProcAddress(hModule, "OfxGetNumberOfPlugins");
    getPlug = (OfxGetPluginFunc)GetProcAddress(hModule, "OfxGetPlugin");
#else
    // POSIX dynamic loading (macOS/Linux)
    handle = dlopen(path.c_str(), RTLD_LAZY | RTLD_LOCAL);
    if (!handle) {
        std::cerr << "[OFX] Failed to dlopen: " << dlerror() << std::endl;
        return false;
    }

    getNumPlugs = (OfxGetNumberOfPluginsFunc)dlsym(handle, "OfxGetNumberOfPlugins");
    getPlug = (OfxGetPluginFunc)dlsym(handle, "OfxGetPlugin");
#endif

    if (!getNumPlugs || !getPlug) {
        std::cerr << "[OFX] Symbols 'OfxGetNumberOfPlugins' or 'OfxGetPlugin' not found." << std::endl;
#ifdef _WIN32
        FreeLibrary((HMODULE)handle);
#else
        dlclose(handle);
#endif
        return false;
    }

    int numPlugins = getNumPlugs();

    for (int i = 0; i < numPlugins; ++i) {
        OfxPlugin* plugin = getPlug(i);
        if (plugin) {
            if (plugin->setHost) plugin->setHost(this->ofxHostStruct);
            if (plugin->mainEntry) plugin->mainEntry(kOfxActionLoad, nullptr, nullptr, nullptr);
            if (plugin->mainEntry) plugin->mainEntry(kOfxActionDescribe, nullptr, nullptr, nullptr);
        }
    }

    PluginLibrary lib;
    lib.libraryHandle = handle;
    lib.path = path;
    lib.pluginCount = numPlugins;
    lib.getPluginFunc = getPlug;
    
    loadedLibraries.push_back(lib);
    return true;
}

void RockyOfxHost::executePluginRender(const std::string& pluginPath, void* srcBuf, void* dstBuf, int width, int height) {
    // 1. Find the library/plugin
    OfxPlugin* targetPlugin = nullptr;
    
    for (auto& lib : loadedLibraries) {
        // Simplified matching: match by file path for now since that's what we store in the Clip
        // Ideally we match by Plugin ID (com.rocky.dummy), but we passed path from UI.
        if (lib.path == pluginPath && lib.pluginCount > 0) {
            targetPlugin = lib.getPluginFunc(0); // Assume first plugin in bundle
            break;
        }
    }
    
    if (!targetPlugin || !targetPlugin->mainEntry) return;

    // 2. Prepare Arguments (Property Set)
    RockyPropertySet args;
    args.name = "RenderArgs";
    args.pointers["Rocky.SrcBuffer"] = srcBuf;
    args.pointers["Rocky.DstBuffer"] = dstBuf;
    args.ints["Rocky.Width"] = width;
    args.ints["Rocky.Height"] = height;
    args.ints["Rocky.RowBytes"] = width * 4; // Assuming RGBA-8bit

    // 3. Call Render Action
    // Note: We use the args as *instance* handle too for this state-less MVP, 
    // or as inArgs. The Dummy plugin just reads inArgs.
    targetPlugin->mainEntry(kOfxImageEffectActionRender, nullptr, (OfxPropertySetHandle)&args, nullptr);
}

void RockyOfxHost::shutdown() {
    for (auto& lib : loadedLibraries) {
        if (lib.libraryHandle) {
#ifdef _WIN32
            FreeLibrary((HMODULE)lib.libraryHandle);
#else
            dlclose(lib.libraryHandle);
#endif
        }
    }
    loadedLibraries.clear();
}
