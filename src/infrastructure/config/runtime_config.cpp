#include "runtime_config.h"
#include <iostream>

namespace rocky {

RuntimeConfig& RuntimeConfig::getInstance() {
    static RuntimeConfig instance;
    return instance;
}

void RuntimeConfig::initialize() {
    if (initialized_) {
        Logger::warning("RuntimeConfig already initialized");
        return;
    }
    
    Logger::info("=== Rocky Video Editor - System Initialization ===");
    
    // 1. Detectar plataforma y hardware
    Logger::info("Detecting platform and hardware...");
    platform_info_ = PlatformDetector::detect();
    Logger::platformInfo(platform_info_);
    
    // 2. Crear perfil de optimización
    Logger::info("Creating optimization profile...");
    opt_profile_ = HardwareOptimizer::createProfile(platform_info_);
    Logger::optimizationProfile(opt_profile_);
    
    // 3. Validar configuración
    if (opt_profile_.preferred_backend == RenderBackend::Software) {
        Logger::warning("No hardware acceleration available, using CPU renderer");
    } else {
        Logger::info("Hardware acceleration enabled");
    }
    
    initialized_ = true;
    Logger::info("System initialization complete");
}

void RuntimeConfig::shutdown() {
    if (!initialized_) {
        return;
    }
    
    Logger::info("Shutting down RuntimeConfig");
    initialized_ = false;
}

void RuntimeConfig::setThreadCount(int threads) {
    if (threads < 1 || threads > 32) {
        Logger::warning("Invalid thread count: " + std::to_string(threads));
        return;
    }
    
    opt_profile_.worker_threads = threads;
    Logger::info("Thread count updated to: " + std::to_string(threads));
}

void RuntimeConfig::setCacheSize(size_t frames) {
    if (frames < 10 || frames > 1000) {
        Logger::warning("Invalid cache size: " + std::to_string(frames));
        return;
    }
    
    opt_profile_.frame_cache_size = frames;
    Logger::info("Cache size updated to: " + std::to_string(frames) + " frames");
}

void RuntimeConfig::setRenderBackend(RenderBackend backend) {
    opt_profile_.preferred_backend = backend;
    
    std::string backend_name;
    switch (backend) {
        case RenderBackend::Metal: backend_name = "Metal"; break;
        case RenderBackend::DirectX11: backend_name = "DirectX 11"; break;
        case RenderBackend::DirectX12: backend_name = "DirectX 12"; break;
        case RenderBackend::Vulkan: backend_name = "Vulkan"; break;
        case RenderBackend::CUDA: backend_name = "CUDA"; break;
        case RenderBackend::Software: backend_name = "Software"; break;
        default: backend_name = "Unknown"; break;
    }
    
    Logger::info("Render backend changed to: " + backend_name);
}

void RuntimeConfig::handleBackendFailure() {
    fallback_count_++;
    
    Logger::error("Render backend failure detected (attempt " + 
                  std::to_string(fallback_count_) + ")");
    
    // Estrategia de fallback progresivo
    if (opt_profile_.preferred_backend == RenderBackend::Metal ||
        opt_profile_.preferred_backend == RenderBackend::DirectX12 ||
        opt_profile_.preferred_backend == RenderBackend::Vulkan ||
        opt_profile_.preferred_backend == RenderBackend::CUDA) {
        
        // Intentar DirectX 11 en Windows, o Software en otros
        if (platform_info_.os == OS::Windows) {
            Logger::info("Falling back to DirectX 11");
            setRenderBackend(RenderBackend::DirectX11);
        } else {
            Logger::info("Falling back to Software renderer");
            setRenderBackend(RenderBackend::Software);
        }
    } else {
        // Ya estamos en fallback, ir a Software
        Logger::critical("Falling back to Software renderer (last resort)");
        setRenderBackend(RenderBackend::Software);
    }
    
    // Si hemos fallado más de 3 veces, algo está muy mal
    if (fallback_count_ > 3) {
        Logger::critical("Multiple backend failures detected - system may be unstable");
    }
}

bool RuntimeConfig::isHardwareAccelerationAvailable() const {
    return opt_profile_.preferred_backend != RenderBackend::Software;
}

} // namespace rocky
