package rocky.core.media;

import org.bytedeco.javacv.FFmpegFrameGrabber;
import java.io.File;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Manages a pool of FFmpegFrameGrabbers to avoid the overhead of 
 * creating/starting/stopping native grabbers frequently.
 */
public class DecoderPool {
    
    // Key: File absolute path
    // Value: Queue of Available (Stopped or Started) Grabbers
    // We pool them by File because a Grabber is bound to a file.
    private static final ConcurrentHashMap<String, ConcurrentLinkedQueue<FFmpegFrameGrabber>> pool = new ConcurrentHashMap<>();

    /**
     * Acquires a grabber for the given file.
     * If one exists in the pool, it is returned. 
     * If not, a new one is created (but NOT started).
     */
    public static FFmpegFrameGrabber acquire(File file) {
        String key = file.getAbsolutePath();
        ConcurrentLinkedQueue<FFmpegFrameGrabber> queue = pool.get(key);
        
        if (queue != null) {
            FFmpegFrameGrabber grabber = queue.poll();
            if (grabber != null) {
                // System.out.println("[DecoderPool] Reusing grabber for: " + file.getName());
                return grabber;
            }
        }
        
        // System.out.println("[DecoderPool] Creating NEW grabber for: " + file.getName());
        return new FFmpegFrameGrabber(file);
    }

    /**
     * Releases a grabber back to the pool.
     * The caller should ensure the grabber is in a reusable state (valid).
     * We do NOT stop it here, allowing the next user to potentially reuse it hot.
     * However, VideoDecoder often restarts, so this is just saving the object/native allocation.
     */
    public static void release(File file, FFmpegFrameGrabber grabber) {
        if (grabber == null || file == null) return;
        
        String key = file.getAbsolutePath();
        pool.computeIfAbsent(key, k -> new ConcurrentLinkedQueue<>()).offer(grabber);
        // System.out.println("[DecoderPool] Returned grabber to pool: " + file.getName());
    }

    /**
     * Completely shuts down the pool and releases all native resources.
     */
    public static void shutdown() {
        System.out.println("[DecoderPool] Shutting down pool...");
        for (ConcurrentLinkedQueue<FFmpegFrameGrabber> queue : pool.values()) {
            FFmpegFrameGrabber g;
            while ((g = queue.poll()) != null) {
                try {
                    g.stop();
                    g.release();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
        pool.clear();
    }
}
