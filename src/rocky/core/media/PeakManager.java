package rocky.core.media;

import java.io.*;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.HashSet;
import java.util.Set;

/**
 * Manages audio peak data for waveform visualization.
 * Mimics Sony Vegas .sfk peak files concept.
 */
public class PeakManager {
    private static PeakManager instance;
    private final Map<String, float[]> peakCache = new HashMap<>();
    private final Set<String> calculating = new HashSet<>();
    private final ExecutorService executor = Executors.newFixedThreadPool(2);
    private final Set<Runnable> updateListeners = new HashSet<>();
    private File cacheDir;

    private PeakManager() {
        String userHome = System.getProperty("user.home");
        cacheDir = new File(userHome, ".rocky_cache/peaks");
        if (!cacheDir.exists()) {
            cacheDir.mkdirs();
        }
    }

    public static PeakManager getInstance() {
        if (instance == null) instance = new PeakManager();
        return instance;
    }

    public void addUpdateListener(Runnable r) {
        synchronized(updateListeners) {
            updateListeners.add(r);
        }
    }

    /**
     * Retrieves peak data for a media source.
     * If not available, triggers a background calculation.
     */
    public float[] getPeaks(String mediaId, String filePath) {
        synchronized(peakCache) {
            if (peakCache.containsKey(mediaId)) {
                return peakCache.get(mediaId);
            }
        }

        // Try loading from disk cache first
        String cacheKey = generateCacheKey(filePath);
        float[] diskPeaks = loadFromDisk(cacheKey);
        if (diskPeaks != null) {
            synchronized(peakCache) {
                peakCache.put(mediaId, diskPeaks);
            }
            return diskPeaks;
        }

        synchronized(calculating) {
            if (!calculating.contains(mediaId)) {
                calculating.add(mediaId);
                executor.submit(() -> {
                    System.out.println("[PeakManager] Starting background calculation for: " + mediaId);
                    float[] peaks = calculatePeaks(filePath);
                    if (peaks != null) {
                        saveToDisk(cacheKey, peaks);
                        synchronized(peakCache) {
                            peakCache.put(mediaId, peaks);
                        }
                    }
                    synchronized(calculating) {
                        calculating.remove(mediaId);
                    }
                    // Notify listeners to repaint
                    synchronized(updateListeners) {
                        for (Runnable r : updateListeners) {
                            javax.swing.SwingUtilities.invokeLater(r);
                        }
                    }
                });
            }
        }
        
        return null;
    }

    private String generateCacheKey(String filePath) {
        return "peak_" + Math.abs(filePath.hashCode());
    }

    private void saveToDisk(String key, float[] peaks) {
        File f = new File(cacheDir, key + ".rocky_peaks");
        try (DataOutputStream dos = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f)))) {
            dos.writeInt(peaks.length);
            for (float p : peaks) {
                dos.writeFloat(p);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private float[] loadFromDisk(String key) {
        File f = new File(cacheDir, key + ".rocky_peaks");
        if (!f.exists()) return null;
        try (DataInputStream dis = new DataInputStream(new BufferedInputStream(new FileInputStream(f)))) {
            int len = dis.readInt();
            float[] peaks = new float[len];
            for (int i = 0; i < len; i++) {
                peaks[i] = dis.readFloat();
            }
            return peaks;
        } catch (IOException e) {
            return null;
        }
    }

    private float[] calculatePeaks(String filePath) {
        // Use a temporary decoder for analysis to not interfere with playback
        AudioDecoder analysisDecoder = new AudioDecoder(new File(filePath));
        if (!analysisDecoder.init()) return null;

        long totalFrames = analysisDecoder.getTotalFrames();
        float[] peaks = new float[(int)totalFrames];

        // Linear read for efficiency
        for (int i = 0; i < totalFrames; i++) {
            // PLAYBACK ISOLATION MODE: Suspend calculation if user hits "Play"
            while (rocky.core.engine.PlaybackIsolation.getInstance().isPlaybackActive()) {
                try {
                    Thread.sleep(200);
                } catch (InterruptedException e) {
                    break;
                }
            }

            short[] samples = analysisDecoder.getAudioSamples(i, 1);
            if (samples != null) {
                float max = 0;
                for (short s : samples) {
                    float v = Math.abs(s) / 32768f;
                    if (v > max) max = v;
                }
                peaks[i] = max;
            }
        }
        analysisDecoder.close();
        System.out.println("[PeakManager] Finished calculation for: " + filePath);
        return peaks;
    }
}
