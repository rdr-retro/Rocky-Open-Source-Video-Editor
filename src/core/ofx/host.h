#pragma once

#include "include/ofxCore.h"
#include "include/ofxImageEffect.h"
#include <string>
#include <vector>
#include <map>

// Forward decl
class OfxPluginContainer;

class RockyOfxHost {
public:
    static RockyOfxHost& getInstance();

    // Initialize the host
    void initialize();

    // Load a plugin bundle/dll
    bool loadPlugin(const std::string& path);

    // Unload all
    void shutdown();

    // The callback passed to the plugin
    static void* fetchSuite(OfxPropertySetHandle host, const char* suiteName, int suiteVersion);

    // Execute the render action for a specific plugin
    void executePluginRender(const std::string& pluginPath, void* srcBuf, void* dstBuf, int width, int height);

private:
    RockyOfxHost();
    ~RockyOfxHost();

    struct PluginLibrary {
        void* libraryHandle; // dlopen handle
        std::string path;
        int pluginCount;
        OfxGetPluginFunc getPluginFunc;
    };

    std::vector<PluginLibrary> loadedLibraries;
    OfxHost* ofxHostStruct;
    struct RockyPropertySet* hostProperties;
};
