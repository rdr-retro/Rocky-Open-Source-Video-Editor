#include "optimizer.h"
#include <algorithm>
#include <cmath>

namespace rocky {

OptimizationProfile HardwareOptimizer::createProfile(const PlatformInfo& platform) {
    OptimizationProfile profile;
    
    // 1. Seleccionar backend de render
    profile.preferred_backend = selectBestRenderer(platform);
    
    // 2. Configurar threading
    profile.worker_threads = calculateOptimalThreads(
        platform.cpu_cores, 
        platform.available_ram_mb
    );
    profile.io_threads = std::max(2, platform.cpu_cores / 4);
    
    // 3. Configurar memoria
    profile.frame_cache_size = calculateCacheSize(
        platform.total_ram_mb,
        platform.available_ram_mb
    );
    
    // Decode buffer: 256MB para sistemas con >8GB, 128MB para menos
    profile.decode_buffer_mb = platform.total_ram_mb > 8000 ? 256 : 128;
    
    // 4. Configurar calidad de preview
    profile.preview_quality = determinePreviewQuality(
        platform.gpu_info,
        platform.gpu_info.vram_mb
    );
    
    // 5. Hardware decode
    profile.use_hardware_decode = platform.has_hardware_decoder;
    
    // 6. GPU export (solo si hay GPU dedicada con suficiente VRAM)
    profile.use_gpu_export = (platform.gpu_info.vram_mb > 2048) &&
                             (profile.preferred_backend != RenderBackend::Software);
    
    profile.export_threads = std::min(profile.worker_threads, 8);
    
    return profile;
}

RenderBackend HardwareOptimizer::selectBestRenderer(const PlatformInfo& platform) {
    // Estrategia: Priorizar aceleración HW nativa > Estabilidad > CPU fallback
    
    if (platform.os == OS::macOS) {
        if (platform.gpu_info.supports_metal) {
            return RenderBackend::Metal;
        }
    }
    
    if (platform.os == OS::Windows) {
        // CUDA para NVIDIA con suficiente VRAM
        if (platform.gpu_info.supports_cuda && 
            platform.gpu_info.vram_mb > 2048 &&
            platform.gpu_info.vendor.find("NVIDIA") != std::string::npos) {
            return RenderBackend::CUDA;
        }
        
        // DirectX 12 para Windows 10+
        if (platform.gpu_info.supports_dx12) {
            return RenderBackend::DirectX12;
        }
        
        // DirectX 11 como fallback estable
        if (platform.gpu_info.supports_dx11) {
            return RenderBackend::DirectX11;
        }
    }
    
    if (platform.os == OS::Linux) {
        // Vulkan preferido en Linux
        if (platform.gpu_info.supports_vulkan) {
            return RenderBackend::Vulkan;
        }
        
        // OpenCL como alternativa
        if (platform.gpu_info.supports_opencl) {
            return RenderBackend::OpenCL;
        }
    }
    
    // Fallback universal: Software renderer (CPU)
    return RenderBackend::Software;
}

int HardwareOptimizer::calculateOptimalThreads(int cpu_cores, size_t available_ram_mb) {
    // Dejar al menos 1 core libre para el sistema
    int max_threads = std::max(1, cpu_cores - 1);
    
    // Limitar según RAM disponible (cada thread necesita ~100MB)
    int ram_limited_threads = static_cast<int>(available_ram_mb / 100);
    
    // Tomar el mínimo, pero al menos 2 threads
    int optimal = std::min(max_threads, ram_limited_threads);
    optimal = std::max(2, optimal);
    
    // Cap a 16 threads (rendimientos decrecientes después)
    return std::min(optimal, 16);
}

size_t HardwareOptimizer::calculateCacheSize(size_t total_ram_mb, size_t available_ram_mb) {
    // Usar hasta 25% de RAM disponible para caché de frames
    size_t cache_budget_mb = available_ram_mb / 4;
    
    // Asumir ~10MB por frame 1080p RGBA
    size_t max_frames = cache_budget_mb / 10;
    
    // Límites razonables
    if (total_ram_mb > 16000) {
        // Sistemas con >16GB: caché grande
        return std::min(max_frames, static_cast<size_t>(300));
    } else if (total_ram_mb > 8000) {
        // Sistemas con 8-16GB: caché medio
        return std::min(max_frames, static_cast<size_t>(150));
    } else {
        // Sistemas con <8GB: caché conservador
        return std::min(max_frames, static_cast<size_t>(50));
    }
}

OptimizationProfile::PreviewQuality HardwareOptimizer::determinePreviewQuality(
    const GPUInfo& gpu, size_t vram_mb) {
    
    // GPU potente: preview a resolución completa
    if (vram_mb > 6000) {
        return OptimizationProfile::PreviewQuality::Full;
    }
    
    // GPU media: 1080p
    if (vram_mb > 4000) {
        return OptimizationProfile::PreviewQuality::High;
    }
    
    // GPU básica: 720p
    if (vram_mb > 2000) {
        return OptimizationProfile::PreviewQuality::Medium;
    }
    
    // GPU integrada o sin GPU: 480p
    return OptimizationProfile::PreviewQuality::Low;
}

} // namespace rocky
