#pragma once
#include "../../platform/common/platform_detector.h"
#include "../../hardware/optimizer.h"
#include "../logging/logger.h"
#include <memory>

namespace rocky {

/**
 * @brief Configuración global del sistema en runtime
 * 
 * Esta clase detecta la plataforma, optimiza configuraciones y
 * proporciona acceso centralizado a la información del sistema.
 */
class RuntimeConfig {
public:
    static RuntimeConfig& getInstance();
    
    // Inicialización del sistema
    void initialize();
    void shutdown();
    
    // Acceso a información
    const PlatformInfo& getPlatformInfo() const { return platform_info_; }
    const OptimizationProfile& getOptimizationProfile() const { return opt_profile_; }
    
    // Configuración dinámica
    void setThreadCount(int threads);
    void setCacheSize(size_t frames);
    void setRenderBackend(RenderBackend backend);
    
    // Fallback handling
    void handleBackendFailure();
    bool isHardwareAccelerationAvailable() const;
    
    // Public destructor for pybind11 compatibility
    ~RuntimeConfig() = default;
    
private:
    RuntimeConfig() = default;
    
    // Prevent copying
    RuntimeConfig(const RuntimeConfig&) = delete;
    RuntimeConfig& operator=(const RuntimeConfig&) = delete;
    
    PlatformInfo platform_info_;
    OptimizationProfile opt_profile_;
    bool initialized_ = false;
    int fallback_count_ = 0;
};

} // namespace rocky
