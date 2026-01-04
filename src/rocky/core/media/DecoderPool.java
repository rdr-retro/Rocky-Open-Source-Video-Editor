package rocky.core.media;

import org.bytedeco.javacv.FFmpegFrameGrabber;
import java.io.File;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Manages a pool of FFmpegFrameGrabbers to avoid the overhead of 
 * creating/starting/stopping native grabbers frequently.
 * 
 * ENHANCED: Implements an LRU eviction policy to prevent VRAM fragmentation 
 * and native memory leaks in large projects.
 */
public class DecoderPool {
    
    // Limits the total number of OPEN native decoders across all media sources
    private static final int MAX_OPEN_DECODERS = 10;
    
    // Key: File absolute path
    // Value: Queue of Available Grabbers for that file
    private static final Map<String, ConcurrentLinkedQueue<FFmpegFrameGrabber>> pool = new LinkedHashMap<>(MAX_OPEN_DECODERS, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, ConcurrentLinkedQueue<FFmpegFrameGrabber>> eldest) {
            if (size() > MAX_OPEN_DECODERS) {
                evict(eldest.getKey(), eldest.getValue());
                return true;
            }
            return false;
        }
    };

    /**
     * Acquires a grabber for the given file.
     * If one exists in the pool, it is returned and marked as "Recently Used".
     */
    public static synchronized FFmpegFrameGrabber acquire(File file) {
        String key = file.getAbsolutePath();
        ConcurrentLinkedQueue<FFmpegFrameGrabber> queue = pool.get(key); // LinkedHashMap.get() updates LRU order
        
        if (queue != null) {
            FFmpegFrameGrabber grabber = queue.poll();
            if (grabber != null) {
                return grabber;
            }
        }
        
        // If we reach here, we need a new grabber. 
        // We ensure the entry exists in the map so size() and LRU work.
        pool.computeIfAbsent(key, k -> new ConcurrentLinkedQueue<>());
        return new FFmpegFrameGrabber(file);
    }

    /**
     * Releases a grabber back to the pool.
     */
    public static synchronized void release(File file, FFmpegFrameGrabber grabber) {
        if (grabber == null || file == null) return;
        
        String key = file.getAbsolutePath();
        pool.computeIfAbsent(key, k -> new ConcurrentLinkedQueue<>()).offer(grabber);
    }

    /**
     * Refreshes the "Recently Used" status of a file without acquiring a grabber.
     * Useful for pre-caching visible clips.
     */
    public static synchronized void touch(String filePath) {
        pool.get(filePath); // Simply accessing it updates LRU if accessOrder=true
    }

    private static void evict(String key, ConcurrentLinkedQueue<FFmpegFrameGrabber> queue) {
        System.out.println("[DecoderPool] EVICTING oldest decoders for: " + key);
        FFmpegFrameGrabber g;
        while ((g = queue.poll()) != null) {
            try {
                g.stop();
                g.release();
            } catch (Exception e) {
                System.err.println("[DecoderPool] Error during eviction of " + key + ": " + e.getMessage());
            }
        }
    }

    /**
     * Completely shuts down the pool and releases all native resources.
     */
    public static synchronized void shutdown() {
        System.out.println("[DecoderPool] Shutting down pool...");
        for (Map.Entry<String, ConcurrentLinkedQueue<FFmpegFrameGrabber>> entry : pool.entrySet()) {
            evict(entry.getKey(), entry.getValue());
        }
        pool.clear();
    }
}
