#pragma once
#include "../platform/common/platform_detector.h"
#include <memory>

namespace rocky {

// Perfil de optimización calculado dinámicamente
struct OptimizationProfile {
    // Threading
    int worker_threads = 4;
    int io_threads = 2;
    
    // Memory
    size_t frame_cache_size = 100;      // Número de frames en caché
    size_t decode_buffer_mb = 256;      // Buffer de decodificación
    
    // Rendering
    RenderBackend preferred_backend = RenderBackend::Software;
    bool use_hardware_decode = true;
    
    // Quality vs Performance
    enum class PreviewQuality {
        Low,      // 480p
        Medium,   // 720p
        High,     // 1080p
        Full      // Resolución original
    };
    PreviewQuality preview_quality = PreviewQuality::Medium;
    
    // Export
    bool use_gpu_export = false;
    int export_threads = 4;
};

// Optimizador de hardware
class HardwareOptimizer {
public:
    // Crear perfil optimizado basado en hardware detectado
    static OptimizationProfile createProfile(const PlatformInfo& platform);
    
    // Seleccionar mejor backend de render
    static RenderBackend selectBestRenderer(const PlatformInfo& platform);
    
    // Calcular número óptimo de hilos
    static int calculateOptimalThreads(int cpu_cores, size_t available_ram_mb);
    
    // Calcular tamaño de caché óptimo
    static size_t calculateCacheSize(size_t total_ram_mb, size_t available_ram_mb);
    
    // Determinar calidad de preview óptima
    static OptimizationProfile::PreviewQuality determinePreviewQuality(
        const GPUInfo& gpu, size_t vram_mb);
};

} // namespace rocky
