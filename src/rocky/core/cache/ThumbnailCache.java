package rocky.core.cache;

import java.awt.image.BufferedImage;
import java.io.File;
import java.util.concurrent.*;
import javax.imageio.ImageIO;
import rocky.core.media.DecoderPool;
import org.bytedeco.javacv.FFmpegFrameGrabber;
import org.bytedeco.javacv.Java2DFrameConverter;
import org.bytedeco.javacv.Frame;

/**
 * Manages thumbnail caching (Memory + Disk) and asynchronous generation.
 * Singleton to be accessed by UI components.
 */
public class ThumbnailCache {
    private static final ThumbnailCache INSTANCE = new ThumbnailCache();
    
    // Memory Cache Config
    private static final int MEM_CACHE_SIZE = 200; // Keep last 200 thumbs in RAM
    private final ConcurrentHashMap<String, BufferedImage> memoryCache = new ConcurrentHashMap<>();
    private final ConcurrentLinkedQueue<String> lruQueue = new ConcurrentLinkedQueue<>();
    
    // Disk Cache Config
    private File cacheDir;
    
    // Generator Thread Pool
    private final ExecutorService generatorExecutor;
    private final ConcurrentHashMap<String, Boolean> pendingRequests = new ConcurrentHashMap<>();

    private ThumbnailCache() {
        // Initialize Cache Directory
        String userHome = System.getProperty("user.home");
        cacheDir = new File(userHome, ".rocky_cache/thumbnails");
        if (!cacheDir.exists()) {
            cacheDir.mkdirs();
        }

        // Single thread for generation to avoid choking the disk/CPU while playing
        // We prioritize playback over thumbnails.
        this.generatorExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "Thumbnail-Generator");
            t.setPriority(Thread.MIN_PRIORITY);
            return t;
        });
    }

    public static ThumbnailCache getInstance() {
        return INSTANCE;
    }

    /**
     * Non-blocking retrieval of a thumbnail.
     * @param mediaPath Absolute path to source file
     * @param frameNumber Frame number to grab
     * @param callback Callback to run on EDT when loaded (only if not in memory)
     * @return The image if in memory, null otherwise.
     */
    public BufferedImage getThumbnail(String mediaPath, long frameNumber, Runnable callback) {
        String key = generateKey(mediaPath, frameNumber);

        // 1. Check Memory
        if (memoryCache.containsKey(key)) {
            // LRU Update
            lruQueue.remove(key);
            lruQueue.add(key);
            return memoryCache.get(key);
        }

        // 2. Check Pending (Avoid redundant work)
        if (pendingRequests.containsKey(key)) {
            return null;
        }

        // 3. Schedule Load/Generate
        pendingRequests.put(key, true);
        generatorExecutor.submit(() -> {
            try {
                BufferedImage thumb = loadFromDisk(key);
                
                if (thumb == null) {
                    thumb = generateThumbnail(mediaPath, frameNumber);
                    if (thumb != null) {
                        saveToDisk(key, thumb);
                    }
                }

                if (thumb != null) {
                    addToMemory(key, thumb);
                    if (callback != null) {
                        javax.swing.SwingUtilities.invokeLater(callback);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                pendingRequests.remove(key);
            }
        });

        return null;
    }

    private String generateKey(String path, long frame) {
        // Simple hash key. Ideally use file hash but path + frame is fast.
        return path.hashCode() + "_" + frame;
    }

    private void addToMemory(String key, BufferedImage img) {
        if (memoryCache.size() >= MEM_CACHE_SIZE) {
            String old = lruQueue.poll();
            if (old != null) memoryCache.remove(old);
        }
        memoryCache.put(key, img);
        lruQueue.add(key);
    }

    private BufferedImage loadFromDisk(String key) {
        File f = new File(cacheDir, key + ".jpg");
        if (f.exists()) {
            try {
                return ImageIO.read(f);
            } catch (Exception e) {
                // corruption?
                f.delete();
            }
        }
        return null;
    }

    private void saveToDisk(String key, BufferedImage img) {
        try {
            ImageIO.write(img, "jpg", new File(cacheDir, key + ".jpg"));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private BufferedImage generateThumbnail(String path, long frameNumber) {
        File file = new File(path);
        if (!file.exists()) return null;

        FFmpegFrameGrabber grabber = null;
        try {
            // Use DecoderPool to efficiently get a grabber
            grabber = DecoderPool.acquire(file);
            
            // We must be careful if the grabber is currently running or stopped.
            // DecoderPool acquire returns it in "as-is" state.
            // But we need random access.
            boolean wasStarted = true;
            try {
                // If it throws exception on getLength, it's not started.
                // Hacky check but effective.
                grabber.getLengthInFrames(); 
            } catch(Exception e) {
                wasStarted = false;
                grabber.start();
            }

            // Set Timestamp
            // Assuming 30fps default for calculation if unknown, but better to use grabber info
            double fps = grabber.getFrameRate();
            if (fps <= 0) fps = 30.0;
            
            long timestamp = (long) ((frameNumber / fps) * 1_000_000L);
            if (timestamp > grabber.getLengthInTime()) timestamp = grabber.getLengthInTime() - 1000;
            if (timestamp < 0) timestamp = 0;

            grabber.setTimestamp(timestamp);
            
            // Grab
            Frame frame = grabber.grabImage();
            if (frame != null && frame.image != null) {
                Java2DFrameConverter converter = new Java2DFrameConverter();
                BufferedImage raw = converter.convert(frame);
                converter.close();
                
                // Scale down for thumbnail (Height 60px is usually enough for timeline track)
                int targetH = 60;
                double ratio = (double)raw.getWidth() / raw.getHeight();
                int targetW = (int) (targetH * ratio);
                
                BufferedImage thumb = new BufferedImage(targetW, targetH, BufferedImage.TYPE_INT_RGB);
                java.awt.Graphics2D g = thumb.createGraphics();
                g.drawImage(raw, 0, 0, targetW, targetH, null);
                g.dispose();
                
                return thumb;
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            if (grabber != null) {
                // Release back to pool. 
                // We leave it started because typically pool items are kept warm.
                DecoderPool.release(file, grabber);
            }
        }
        return null;
    }

    public void clearCache() {
        memoryCache.clear();
        lruQueue.clear();
        // Optional: clear disk cache? No, keep it persistent.
    }
}
