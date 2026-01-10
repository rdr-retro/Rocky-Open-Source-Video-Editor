#include "platform_detector.h"
#include <thread>
#include <iostream>

// Platform-specific includes
#ifdef _WIN32
    #include <windows.h>
    #include <sysinfoapi.h>
#elif __APPLE__
    #include <sys/types.h>
    #include <sys/sysctl.h>
    #include <mach/mach.h>
    #include <TargetConditionals.h>
#elif __linux__
    #include <sys/sysinfo.h>
    #include <fstream>
    #include <unistd.h>
#endif

// CPU feature detection
#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
    #include <cpuid.h>
#endif

namespace rocky {

PlatformInfo PlatformDetector::detect() {
    PlatformInfo info;
    
    info.os = OS::Unknown;
    info.os_name = getOSName();
    info.os_version = getOSVersion();
    
    #ifdef _WIN32
        info.os = OS::Windows;
    #elif __APPLE__
        info.os = OS::macOS;
    #elif __linux__
        info.os = OS::Linux;
    #endif
    
    info.cpu_cores = getCPUCores();
    info.cpu_features = detectCPUFeatures();
    info.total_ram_mb = getTotalRAM();
    info.available_ram_mb = getAvailableRAM();
    info.gpu_info = detectGPU();
    info.has_hardware_decoder = checkHardwareDecoder();
    
    return info;
}

std::string PlatformDetector::getOSName() {
    #ifdef _WIN32
        return "Windows";
    #elif __APPLE__
        return "macOS";
    #elif __linux__
        return "Linux";
    #else
        return "Unknown";
    #endif
}

std::string PlatformDetector::getOSVersion() {
    #ifdef _WIN32
        // Windows version detection
        OSVERSIONINFOEX osvi;
        ZeroMemory(&osvi, sizeof(OSVERSIONINFOEX));
        osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFOEX);
        
        if (GetVersionEx((OSVERSIONINFO*)&osvi)) {
            return std::to_string(osvi.dwMajorVersion) + "." + 
                   std::to_string(osvi.dwMinorVersion);
        }
        return "Unknown";
        
    #elif __APPLE__
        // macOS version from sysctl
        char version[256];
        size_t size = sizeof(version);
        if (sysctlbyname("kern.osproductversion", version, &size, NULL, 0) == 0) {
            return std::string(version);
        }
        return "Unknown";
        
    #elif __linux__
        // Linux kernel version
        std::ifstream version_file("/proc/version");
        if (version_file.is_open()) {
            std::string line;
            std::getline(version_file, line);
            // Parse version from line
            size_t pos = line.find("version ");
            if (pos != std::string::npos) {
                size_t end = line.find(" ", pos + 8);
                return line.substr(pos + 8, end - pos - 8);
            }
        }
        return "Unknown";
    #else
        return "Unknown";
    #endif
}

int PlatformDetector::getCPUCores() {
    int cores = std::thread::hardware_concurrency();
    return cores > 0 ? cores : 1;
}

CPUFeatures PlatformDetector::detectCPUFeatures() {
    CPUFeatures features;
    
    #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
        unsigned int eax, ebx, ecx, edx;
        
        // Check CPUID support
        if (__get_cpuid(1, &eax, &ebx, &ecx, &edx)) {
            features.has_sse2 = (edx & (1 << 26)) != 0;
            features.has_sse4 = (ecx & (1 << 19)) != 0;
            features.has_avx = (ecx & (1 << 28)) != 0;
        }
        
        // Extended features
        if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx)) {
            features.has_avx2 = (ebx & (1 << 5)) != 0;
            features.has_avx512 = (ebx & (1 << 16)) != 0;
        }
    #elif defined(__aarch64__) || defined(_M_ARM64)
        // ARM64 (Apple Silicon, etc.) - all modern ARM64 has NEON
        features.has_sse2 = true; // Equivalent capability via NEON
    #endif
    
    return features;
}

size_t PlatformDetector::getTotalRAM() {
    #ifdef _WIN32
        MEMORYSTATUSEX memInfo;
        memInfo.dwLength = sizeof(MEMORYSTATUSEX);
        GlobalMemoryStatusEx(&memInfo);
        return static_cast<size_t>(memInfo.ullTotalPhys / (1024 * 1024));
        
    #elif __APPLE__
        int64_t ram = 0;
        size_t size = sizeof(ram);
        if (sysctlbyname("hw.memsize", &ram, &size, NULL, 0) == 0) {
            return static_cast<size_t>(ram / (1024 * 1024));
        }
        return 0;
        
    #elif __linux__
        struct sysinfo info;
        if (sysinfo(&info) == 0) {
            return static_cast<size_t>(info.totalram / (1024 * 1024));
        }
        return 0;
    #else
        return 0;
    #endif
}

size_t PlatformDetector::getAvailableRAM() {
    #ifdef _WIN32
        MEMORYSTATUSEX memInfo;
        memInfo.dwLength = sizeof(MEMORYSTATUSEX);
        GlobalMemoryStatusEx(&memInfo);
        return static_cast<size_t>(memInfo.ullAvailPhys / (1024 * 1024));
        
    #elif __APPLE__
        mach_port_t host_port = mach_host_self();
        mach_msg_type_number_t host_size = sizeof(vm_statistics_data_t) / sizeof(integer_t);
        vm_size_t pagesize;
        vm_statistics_data_t vm_stat;
        
        host_page_size(host_port, &pagesize);
        
        if (host_statistics(host_port, HOST_VM_INFO, (host_info_t)&vm_stat, &host_size) == KERN_SUCCESS) {
            size_t free_memory = (vm_stat.free_count + vm_stat.inactive_count) * pagesize;
            return static_cast<size_t>(free_memory / (1024 * 1024));
        }
        return 0;
        
    #elif __linux__
        struct sysinfo info;
        if (sysinfo(&info) == 0) {
            return static_cast<size_t>(info.freeram / (1024 * 1024));
        }
        return 0;
    #else
        return 0;
    #endif
}

GPUInfo PlatformDetector::detectGPU() {
    GPUInfo gpu;
    
    #ifdef __APPLE__
        // macOS: Always has Metal support on modern systems
        gpu.vendor = "Apple/AMD";
        gpu.model = "Integrated GPU";
        gpu.supports_metal = true;
        
        // Estimate VRAM (macOS shares system RAM)
        gpu.vram_mb = getTotalRAM() / 4; // Rough estimate
        
    #elif _WIN32
        // Windows: Will implement DirectX detection in platform/windows/
        gpu.vendor = "Unknown";
        gpu.supports_dx11 = true; // Assume DX11 available on Windows
        gpu.vram_mb = 2048; // Default assumption
        
    #elif __linux__
        // Linux: Will implement Vulkan detection in platform/linux/
        gpu.vendor = "Unknown";
        gpu.supports_vulkan = true; // Assume Vulkan available
        gpu.vram_mb = 2048; // Default assumption
    #endif
    
    return gpu;
}

bool PlatformDetector::checkHardwareDecoder() {
    #ifdef __APPLE__
        // VideoToolbox is available on macOS 10.8+
        return true;
    #elif _WIN32
        // Media Foundation available on Windows 7+
        return true;
    #elif __linux__
        // Check for VA-API or VDPAU (simplified check)
        return true;
    #else
        return false;
    #endif
}

} // namespace rocky
