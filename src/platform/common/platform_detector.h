#pragma once
#include <string>
#include <vector>

namespace rocky {

// Enumeraciones de plataforma
enum class OS {
    Unknown,
    Windows,
    macOS,
    Linux
};

enum class RenderBackend {
    Software,      // CPU fallback (siempre disponible)
    Metal,         // macOS
    DirectX11,     // Windows
    DirectX12,     // Windows (moderno)
    Vulkan,        // Linux/Windows
    CUDA,          // NVIDIA (Windows/Linux)
    OpenCL         // Multi-plataforma
};

// Información de GPU
struct GPUInfo {
    std::string vendor;           // "NVIDIA", "AMD", "Intel", "Apple"
    std::string model;            // "GeForce RTX 3080"
    size_t vram_mb = 0;          // VRAM en MB
    
    // Capacidades por API
    bool supports_metal = false;
    bool supports_dx11 = false;
    bool supports_dx12 = false;
    bool supports_vulkan = false;
    bool supports_cuda = false;
    bool supports_opencl = false;
};

// Características de CPU
struct CPUFeatures {
    bool has_sse2 = false;
    bool has_sse4 = false;
    bool has_avx = false;
    bool has_avx2 = false;
    bool has_avx512 = false;
};

// Información completa de plataforma
struct PlatformInfo {
    OS os = OS::Unknown;
    std::string os_name;
    std::string os_version;
    
    // CPU
    int cpu_cores = 1;
    CPUFeatures cpu_features;
    
    // Memoria
    size_t total_ram_mb = 0;
    size_t available_ram_mb = 0;
    
    // GPU
    GPUInfo gpu_info;
    
    // Capacidades del sistema
    bool has_hardware_decoder = false;
    std::vector<std::string> supported_codecs;
};

// Clase principal de detección
class PlatformDetector {
public:
    static PlatformInfo detect();
    
private:
    static std::string getOSName();
    static std::string getOSVersion();
    static int getCPUCores();
    static CPUFeatures detectCPUFeatures();
    static size_t getTotalRAM();
    static size_t getAvailableRAM();
    static GPUInfo detectGPU();
    static bool checkHardwareDecoder();
};

} // namespace rocky
