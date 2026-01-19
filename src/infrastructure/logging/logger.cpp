#include "logger.h"
#include <iostream>
#include <chrono>
#include <iomanip>

namespace rocky {

std::ofstream Logger::log_file_;
bool Logger::initialized_ = false;

void Logger::init(const std::string& log_file_path) {
    if (!initialized_) {
        log_file_.open(log_file_path, std::ios::out | std::ios::app);
        initialized_ = true;
        info("Logger initialized: " + log_file_path);
    }
}

void Logger::shutdown() {
    if (initialized_) {
        info("Logger shutting down");
        log_file_.close();
        initialized_ = false;
    }
}

void Logger::debug(const std::string& message) {
    log(Level::Debug, message);
}

void Logger::info(const std::string& message) {
    log(Level::Info, message);
}

void Logger::warning(const std::string& message) {
    log(Level::Warning, message);
}

void Logger::error(const std::string& message) {
    log(Level::Error, message);
}

void Logger::critical(const std::string& message) {
    log(Level::Critical, message);
}

void Logger::platformInfo(const PlatformInfo& platform) {
    std::ostringstream oss;
    oss << "=== Platform Information ===" << std::endl;
    oss << "OS: " << platform.os_name << " " << platform.os_version << std::endl;
    oss << "CPU: " << platform.cpu_cores << " cores" << std::endl;
    oss << "  - SSE2: " << (platform.cpu_features.has_sse2 ? "Yes" : "No") << std::endl;
    oss << "  - AVX: " << (platform.cpu_features.has_avx ? "Yes" : "No") << std::endl;
    oss << "  - AVX2: " << (platform.cpu_features.has_avx2 ? "Yes" : "No") << std::endl;
    oss << "RAM: " << platform.total_ram_mb << " MB total, " 
        << platform.available_ram_mb << " MB available" << std::endl;
    oss << "GPU: " << platform.gpu_info.vendor << " " << platform.gpu_info.model << std::endl;
    oss << "  - VRAM: " << platform.gpu_info.vram_mb << " MB" << std::endl;
    oss << "  - Metal: " << (platform.gpu_info.supports_metal ? "Yes" : "No") << std::endl;
    oss << "  - DirectX 11: " << (platform.gpu_info.supports_dx11 ? "Yes" : "No") << std::endl;
    oss << "  - Vulkan: " << (platform.gpu_info.supports_vulkan ? "Yes" : "No") << std::endl;
    oss << "Hardware Decoder: " << (platform.has_hardware_decoder ? "Available" : "Not available");
    
    info(oss.str());
}

void Logger::optimizationProfile(const OptimizationProfile& profile) {
    std::ostringstream oss;
    oss << "=== Optimization Profile ===" << std::endl;
    oss << "Worker Threads: " << profile.worker_threads << std::endl;
    oss << "IO Threads: " << profile.io_threads << std::endl;
    oss << "Frame Cache: " << profile.frame_cache_size << " frames" << std::endl;
    oss << "Decode Buffer: " << profile.decode_buffer_mb << " MB" << std::endl;
    
    std::string backend_name;
    switch (profile.preferred_backend) {
        case RenderBackend::Metal: backend_name = "Metal"; break;
        case RenderBackend::DirectX11: backend_name = "DirectX 11"; break;
        case RenderBackend::DirectX12: backend_name = "DirectX 12"; break;
        case RenderBackend::Vulkan: backend_name = "Vulkan"; break;
        case RenderBackend::CUDA: backend_name = "CUDA"; break;
        case RenderBackend::Software: backend_name = "Software (CPU)"; break;
        default: backend_name = "Unknown"; break;
    }
    oss << "Render Backend: " << backend_name << std::endl;
    
    oss << "Hardware Decode: " << (profile.use_hardware_decode ? "Enabled" : "Disabled") << std::endl;
    oss << "GPU Export: " << (profile.use_gpu_export ? "Enabled" : "Disabled");
    
    info(oss.str());
}

void Logger::log(Level level, const std::string& message) {
    std::string timestamp = getCurrentTimestamp();
    std::string level_str = levelToString(level);
    std::string full_message = "[" + timestamp + "] [" + level_str + "] " + message;
    
    // Console output
    std::cout << full_message << std::endl;
    
    // File output
    if (initialized_ && log_file_.is_open()) {
        log_file_ << full_message << std::endl;
        log_file_.flush();
    }
}

std::string Logger::levelToString(Level level) {
    switch (level) {
        case Level::Debug: return "DEBUG";
        case Level::Info: return "INFO";
        case Level::Warning: return "WARNING";
        case Level::Error: return "ERROR";
        case Level::Critical: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

std::string Logger::getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    
    std::ostringstream oss;
    
    #ifdef _WIN32
        struct tm tm_info;
        if (localtime_s(&tm_info, &time) == 0) {
            oss << std::put_time(&tm_info, "%Y-%m-%d %H:%M:%S");
        } else {
            oss << "0000-00-00 00:00:00"; // Fallback
        }
    #else
        // POSIX thread-safe localtime
        struct tm tm_info;
        localtime_r(&time, &tm_info);
        oss << std::put_time(&tm_info, "%Y-%m-%d %H:%M:%S");
    #endif

    oss << '.' << std::setfill('0') << std::setw(3) << ms.count();
    
    return oss.str();
}

} // namespace rocky
