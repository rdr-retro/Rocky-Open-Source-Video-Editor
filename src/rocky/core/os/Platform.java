package rocky.core.os;

/**
 * Centralized platform detection and optimization heuristics.
 */
public class Platform {
    public static final boolean IS_MAC = System.getProperty("os.name").toLowerCase().contains("mac");
    public static final boolean IS_WINDOWS = System.getProperty("os.name").toLowerCase().contains("win");
    public static final boolean IS_LINUX = System.getProperty("os.name").toLowerCase().contains("nux") || System.getProperty("os.name").toLowerCase().contains("nix");
    
    public static final boolean IS_APPLE_SILICON = IS_MAC && "aarch64".equals(System.getProperty("os.arch"));
    
    public static String getOSName() {
        if (IS_MAC) return "macOS";
        if (IS_WINDOWS) return "Windows";
        if (IS_LINUX) return "Linux";
        return System.getProperty("os.name");
    }

    public static String getOptimizationProfile() {
        if (IS_APPLE_SILICON) {
            return "Apple Silicon (Zero-Stutter Mode Active)";
        } else if (IS_WINDOWS) {
            return "Windows Generic (DirectX/NVENC capable)";
        } else {
            return "Generic x86 Compatibility Mode";
        }
    }

    /**
     * Returns the recommended FFmpeg video encoder for this platform.
     */
    public static String getHardwareEncoder() {
        if (IS_MAC) {
            // Apple Silicon and Intel Macs both support VideoToolbox
            return "h264_videotoolbox"; 
        } else if (IS_WINDOWS) {
            String gpu = detectWindowsGraphics();
            if (gpu.contains("nvidia") || gpu.contains("geforce") || gpu.contains("quadro")) {
                return "h264_nvenc";
            } else if (gpu.contains("amd") || gpu.contains("radeon")) {
                return "h264_amf"; 
            } else if (gpu.contains("intel") || gpu.contains("uhd") || gpu.contains("iris")) {
                return "h264_qsv";
            }
            return "libx264"; 
        } else {
            return "libx264";
        }
    }
    
    public static boolean supportsHardwareBitrate() {
        // VideoToolbox (Mac) requires bitrate (-b:v) instead of CRF
        return IS_MAC; 
    }
    private static String cachedGpuName = null;

    private static String detectWindowsGraphics() {
        if (cachedGpuName != null) return cachedGpuName;
        
        try {
            Process p = Runtime.getRuntime().exec("wmic path win32_VideoController get name");
            java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(p.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line.toLowerCase());
            }
            cachedGpuName = sb.toString();
            return cachedGpuName;
        } catch (Exception e) {
            System.err.println("[Platform] Error detecting Windows GPU: " + e.getMessage());
            return "unknown";
        }
    }
    
    /**
     * Applies system-wide optimizations and returns the recommended Audio/Video Sync Latency.
     * Use this at startup.
     * @return latency compensation in seconds (e.g. 0.15 for Mac).
     */
    public static double applyOptimizations() {
        if (IS_MAC) {
            System.setProperty("sun.java2d.opengl", "true");
            System.setProperty("apple.awt.application.appearance", "system");
            System.setProperty("apple.laf.useScreenMenuBar", "true");
            // INCREASED: 0.25s for HEVC which is 3-5x slower than H.264
            return 0.25; // Tuned for CoreAudio + VideoToolbox HEVC latency
        } else if (IS_WINDOWS) {
            System.setProperty("sun.java2d.d3d", "true");
            System.setProperty("sun.java2d.ddscale", "true");
            return 0.20; // DirectSound often has higher latency buffer
        } else if (IS_LINUX) {
            System.setProperty("sun.java2d.xrender", "true");
            return 0.12; // Pulse/ALSA is usually quite snappy
        } else {
            return 0.10; // Generic fallback
        }
    }
}
