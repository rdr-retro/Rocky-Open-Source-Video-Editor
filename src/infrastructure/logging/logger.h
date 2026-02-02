#pragma once
#include "../../platform/common/platform_detector.h"
#include "../../hardware/optimizer.h"
#include <string>
#include <fstream>
#include <sstream>

namespace rocky {

// Sistema de logging multiplataforma
class Logger {
public:
    enum class Level {
        Debug,
        Info,
        Warning,
        Error,
        Critical
    };
    
    static void init(const std::string& log_file_path);
    static void shutdown();
    
    static void debug(const std::string& message);
    static void info(const std::string& message);
    static void warning(const std::string& message);
    static void error(const std::string& message);
    static void critical(const std::string& message);
    
    // Logging específico de plataforma
    static void platformInfo(const PlatformInfo& platform);
    static void optimizationProfile(const OptimizationProfile& profile);
    
private:
    static void log(Level level, const std::string& message);
    static std::string levelToString(Level level);
    static std::string getCurrentTimestamp();
    
    static std::ofstream log_file_;
    static bool initialized_;
};

} // namespace rocky
