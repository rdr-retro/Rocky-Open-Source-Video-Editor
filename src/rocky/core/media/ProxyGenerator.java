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

    public static void generateProxy(File source, int targetHeight, String bitrate, Consumer<String> onComplete) {
        executor.submit(() -> {
            // PLAYBACK ISOLATION: Pause proxy generation while user is watching video
            while (rocky.core.engine.PlaybackIsolation.getInstance().isPlaybackActive()) {
                try { Thread.sleep(1000); } catch (InterruptedException e) { break; }
            }

            try {
                File proxyDir = new File(source.getParent(), ".proxies");
                if (!proxyDir.exists())
                    proxyDir.mkdirs();

                String proxyName = source.getName() + "_" + targetHeight + "p_proxy.mp4";
                File proxyFile = new File(proxyDir, proxyName);

                if (proxyFile.exists()) {
                    onComplete.accept(proxyFile.getAbsolutePath());
                    return;
                }

                System.out.println("[ProxyGenerator] Generating proxy for: " + source.getName() + " (" + targetHeight
                        + "p, " + bitrate + ")");

                // Low-res proxy (variable height, fast preset, AAC audio)
                String[] cmd = {
                        "ffmpeg", "-i", source.getAbsolutePath(),
                        "-vf", "scale=-2:" + targetHeight,
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                        "-b:v", bitrate,
                        "-c:a", "aac", "-b:a", "128k",
                        "-y", proxyFile.getAbsolutePath()
                };

                Process p = new ProcessBuilder(cmd)
                        .inheritIO()
                        .start();
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
