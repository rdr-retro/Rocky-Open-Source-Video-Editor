package egine.media;

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

    private PeakManager() {}

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

        synchronized(calculating) {
            if (!calculating.contains(mediaId)) {
                calculating.add(mediaId);
                executor.submit(() -> {
                    System.out.println("[PeakManager] Starting background calculation for: " + mediaId);
                    float[] peaks = calculatePeaks(filePath);
                    if (peaks != null) {
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

    private float[] calculatePeaks(String filePath) {
        // Use a temporary decoder for analysis to not interfere with playback
        AudioDecoder analysisDecoder = new AudioDecoder(new File(filePath));
        if (!analysisDecoder.init()) return null;

        long totalFrames = analysisDecoder.getTotalFrames();
        float[] peaks = new float[(int)totalFrames];

        // Linear read for efficiency
        for (int i = 0; i < totalFrames; i++) {
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
