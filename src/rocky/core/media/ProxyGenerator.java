package rocky.core.media;

import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

/**
 * Service to generate low-resolution proxy files in the background.
 */
public class ProxyGenerator {
    private static final ExecutorService executor = Executors.newFixedThreadPool(1);
    
    public static void generateProxy(File source, Consumer<String> onComplete) {
        executor.submit(() -> {
            try {
                File proxyDir = new File(source.getParent(), ".proxies");
                if (!proxyDir.exists()) proxyDir.mkdirs();
                
                String proxyName = source.getName() + "_proxy.mp4";
                File proxyFile = new File(proxyDir, proxyName);
                
                if (proxyFile.exists()) {
                    onComplete.accept(proxyFile.getAbsolutePath());
                    return;
                }
                
                System.out.println("[ProxyGenerator] Generating proxy for: " + source.getName());
                
                // Low-res proxy (480p, fast preset, AAC audio)
                String[] cmd = {
                    "ffmpeg", "-i", source.getAbsolutePath(),
                    "-vf", "scale=-2:480",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-c:a", "aac", "-b:a", "128k",
                    "-y", proxyFile.getAbsolutePath()
                };
                
                Process p = new ProcessBuilder(cmd).start();
                int result = p.waitFor();
                
                if (result == 0) {
                    System.out.println("[ProxyGenerator] Proxy READY: " + proxyFile.getName());
                    onComplete.accept(proxyFile.getAbsolutePath());
                } else {
                    System.err.println("[ProxyGenerator] Failed to generate proxy. FFmpeg exit code: " + result);
                }
                
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }
}
