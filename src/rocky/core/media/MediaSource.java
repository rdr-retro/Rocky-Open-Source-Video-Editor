package rocky.core.media;

import java.io.File;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.util.ArrayList;
import java.util.List;

/**
 * Represents a physical media file (the "Source" of the 3-layer architecture).
 */
public class MediaSource {
    private String id;
    private String filePath;
    private long totalFrames;
    private int width;
    private int height;
    private BufferedImage cachedImage;
    private VideoDecoder videoDecoder;
    private AudioDecoder audioDecoder;
    private boolean isVideo;
    private boolean isAudio;

    // Performance Optimization for GIFs and short animations
    private java.util.List<java.awt.image.BufferedImage> gifFrameCache;
    private long currentCacheBytes = 0;
    private final long MAX_CACHE_BYTES = 200 * 1024 * 1024; // 200 MB limit per source

    // Proxy support (Dual-stream architecture)
    private String proxyFilePath;
    private VideoDecoder proxyDecoder;
    private boolean proxyUsed = false;
    private boolean generatingProxy = false;

    private final java.util.LinkedHashMap<Long, BufferedImage> lruFrameCache = new java.util.LinkedHashMap<Long, BufferedImage>(
            32, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(java.util.Map.Entry<Long, BufferedImage> eldest) {
            if (currentCacheBytes > MAX_CACHE_BYTES) {
                BufferedImage img = eldest.getValue();
                if (img != null) {
                    currentCacheBytes -= (long) img.getWidth() * img.getHeight() * 4;
                }
                return true;
            }
            return false;
        }
    };

    public MediaSource(String id, String filePath, double previewScale) {
        this.id = id;
        this.filePath = filePath;

        String lower = filePath.toLowerCase();
        this.isVideo = lower.endsWith(".mp4") || lower.endsWith(".avi") ||
                lower.endsWith(".mov") || lower.endsWith(".mkv") ||
                lower.endsWith(".m4v") || lower.endsWith(".ts") ||
                lower.endsWith(".webm") || lower.endsWith(".flv") ||
                lower.endsWith(".gif");
        this.isAudio = lower.endsWith(".mp3") || lower.endsWith(".wav") ||
                lower.endsWith(".aac") || lower.endsWith(".m4a") ||
                lower.endsWith(".ogg") || lower.endsWith(".flac") ||
                lower.endsWith(".caf");

        if (isVideo) {
            this.videoDecoder = new VideoDecoder(new File(filePath), -1, -1);
            double scale = previewScale;
            // Native Proxy cap for initial load if we had access to props (but we don't
            // here easily)
            // Strategy: MediaSource is usually created from TimelinePanel or ProjectManager
            // which passes props.getPreviewScale()
            // We trust the caller but we can add an extra safety check if needed.
            this.videoDecoder.setScaleFactor(scale);
            if (this.videoDecoder.init()) {
                this.totalFrames = this.videoDecoder.getTotalFrames();
                this.width = this.videoDecoder.getWidth();
                this.height = this.videoDecoder.getHeight();

                // If it's a GIF, cache all frames to memory (if it fits in a reasonable budget)
                // Limit: 200 frames AND total pixels < 200MB (approx 50MP)
                long totalPixels = (long) width * height * totalFrames;
                if (lower.endsWith(".gif") && totalFrames > 0 && totalFrames < 200 && totalPixels < 50_000_000) {
                    System.out.println("[MediaSource] Pro-actively caching GIF frames: " + filePath);
                    gifFrameCache = new ArrayList<>();
                    for (int i = 0; i < totalFrames; i++) {
                        BufferedImage frame = videoDecoder.getFrame(i);
                        if (frame != null) {
                            gifFrameCache.add(cloneToARGBPre(frame));
                        }
                    }
                    System.out.println("[MediaSource] Cached " + gifFrameCache.size() + " frames for GIF.");
                }
            }
        }

        // Try audio initialization for both video and audio files
        if (isVideo || isAudio) {
            this.audioDecoder = new AudioDecoder(new File(filePath));
            if (this.audioDecoder.init() && this.audioDecoder.hasAudio()) {
                if (isAudio) {
                    this.totalFrames = this.audioDecoder.getTotalFrames();
                }
                System.out.println("[MediaSource] Audio probe SUCCESS: " + filePath);
            } else {
                System.out.println("[MediaSource] Audio probe FAILED or NO audio: " + filePath);
                this.audioDecoder.close();
                this.audioDecoder = null;
            }
        }

        if (!isVideo && !isAudio) {
            // Image handling (Default 3 seconds @ 30 FPS)
            this.totalFrames = 90;
            this.width = 1920;
            this.height = 1080;
        }
    }

    public String getId() {
        return id;
    }

    public String getFilePath() {
        return filePath;
    }

    public long getTotalFrames() {
        return totalFrames;
    }

    public int getWidth() {
        return width;
    }

    public int getHeight() {
        return height;
    }

    public boolean isVideo() {
        return isVideo;
    }

    public boolean isAudio() {
        return isAudio;
    }

    public boolean hasAudio() {
        if (isAudio)
            return true;
        return audioDecoder != null;
    }

    public short[] getAudioSamples(long index) {
        if (audioDecoder != null) {
            if (index >= totalFrames) {
                // Return silence (zeros) for out-of-bounds requests
                return new short[audioDecoder.getSamplesPerFrame()];
            }
            return audioDecoder.getAudioSamples(index, 1);
        }
        return null;
    }

    public short[] getAudioSampleAt(long sampleIndex) {
        if (audioDecoder != null) {
            return audioDecoder.getAudioSampleAt(sampleIndex);
        }
        return new short[] { 0, 0 };
    }

    private BufferedImage cloneToARGBPre(BufferedImage src) {
        if (src == null)
            return null;
        // Standardize on TYPE_INT_ARGB_PRE for the entire pipe
        BufferedImage dest = new BufferedImage(src.getWidth(), src.getHeight(), BufferedImage.TYPE_INT_ARGB_PRE);
        java.awt.Graphics2D g = dest.createGraphics();
        g.drawImage(src, 0, 0, null);
        g.dispose();
        return dest;
    }

    // Performance: Store current scale to apply to proxies too
    private double currentScale = 1.0;

    public void reinitDecoder(double scale) {
        if (!isVideo)
            return;

        this.currentScale = scale;
        System.out.println("[MediaSource] Re-initializing decoder for " + id + " with scale " + scale);

        if (videoDecoder != null) {
            videoDecoder.close();
        }
        if (proxyDecoder != null) {
            proxyDecoder.close();
            proxyDecoder = null;
        }

        synchronized (lruFrameCache) {
            lruFrameCache.clear();
            currentCacheBytes = 0;
        }

        this.videoDecoder = new VideoDecoder(new File(filePath), -1, -1);
        this.videoDecoder.setScaleFactor(scale);
        if (this.videoDecoder.init()) {
            this.width = this.videoDecoder.getWidth();
            this.height = this.videoDecoder.getHeight();
        }

        // Re-load proxy if it was active
        if (proxyFilePath != null) {
            setupProxy(proxyFilePath);
        }
    }

    public void setupProxy(String path) {
        this.proxyFilePath = path;
        if (proxyDecoder != null)
            proxyDecoder.close();

        this.proxyDecoder = new VideoDecoder(new File(path), -1, -1);
        // Apply the global visor scale to the proxy as well for maximum performance
        this.proxyDecoder.setScaleFactor(this.currentScale);
        if (this.proxyDecoder.init()) {
            System.out.println(
                    "[MediaSource] Proxy decoder initialized: " + path + " (Scale: " + this.currentScale + ")");
        }
    }

    public void setProxyUsed(boolean used) {
        this.proxyUsed = used;
        // Clear cache when switching modes to prevent visual mixed-resolution artifacts
        synchronized (lruFrameCache) {
            lruFrameCache.clear();
            currentCacheBytes = 0;
        }
    }

    public boolean isProxyActive() {
        return proxyUsed && proxyDecoder != null;
    }

    public String getProxyFilePath() {
        return proxyFilePath;
    }

    public boolean isGeneratingProxy() {
        return generatingProxy;
    }

    public void setGeneratingProxy(boolean b) {
        this.generatingProxy = b;
    }

    public BufferedImage getFrame(long index) {
        return getFrame(index, false);
    }

    // Dedicated decoder for High Quality Renders (Bypasses Visor Scaling)
    private VideoDecoder renderDecoder;

    public BufferedImage getFrame(long index, boolean forceOriginal) {
        if (gifFrameCache != null && !gifFrameCache.isEmpty()) {
            return gifFrameCache.get((int) (index % gifFrameCache.size()));
        }

        long finalIndex = index;
        if (isVideo && videoDecoder != null) {
            if (filePath.toLowerCase().endsWith(".gif") && totalFrames > 0) {
                finalIndex = index % totalFrames;
            } else {
                finalIndex = Math.min(index, totalFrames - 1);
            }

            // --- RENDER PATH (High Quality) ---
            if (forceOriginal) {
                // If the Visor is scaled (e.g. 1/4), the main videoDecoder is low-res.
                // We MUST use a separate Full Res decoder for rendering to avoid pixelation.
                if (currentScale < 0.99) {
                    synchronized (this) {
                        if (renderDecoder == null) {
                            renderDecoder = new VideoDecoder(new File(filePath), -1, -1);
                            renderDecoder.setScaleFactor(1.0); // STRICTLY FULL RES
                            if (renderDecoder.init()) {
                                System.out.println("[MediaSource] Initialized dedicated RenderDecoder for: " + id);
                            } else {
                                System.err.println("[MediaSource] Failed to init RenderDecoder for: " + id);
                            }
                        }
                    }
                    if (renderDecoder != null) {
                        synchronized (renderDecoder) {
                            BufferedImage fullRes = renderDecoder.getFrame(finalIndex);
                            return cloneToARGBPre(fullRes);
                        }
                    }
                }
                // If not scaled, or renderDecoder failed, fall through to main decoder (better
                // than nothing)
            }

            // --- PREVIEW PATH (Visor/Proxy) ---
            synchronized (lruFrameCache) {
                if (lruFrameCache.containsKey(finalIndex)) {
                    return lruFrameCache.get(finalIndex);
                }
            }

            BufferedImage frame;
            synchronized (videoDecoder) {
                // Determine which decoder to use
                if (!forceOriginal && proxyUsed && proxyDecoder != null) {
                    frame = proxyDecoder.getFrame(finalIndex);
                } else {
                    frame = videoDecoder.getFrame(finalIndex);
                }
            }

            if (frame != null) {
                BufferedImage optimized = cloneToARGBPre(frame);
                synchronized (lruFrameCache) {
                    lruFrameCache.put(finalIndex, optimized);
                    currentCacheBytes += (long) optimized.getWidth() * optimized.getHeight() * 4;
                }
                return optimized;
            }
        }
        return getOrLoadImage();
    }

    public BufferedImage getOrLoadImage() {
        if (cachedImage == null) {
            String lower = filePath.toLowerCase();
            boolean isWebP = lower.endsWith(".webp");

            // Strategy 1: Attempt ImageIO (Native Java)
            try {
                cachedImage = ImageIO.read(new File(filePath));
                if (cachedImage != null) {
                    this.width = cachedImage.getWidth();
                    this.height = cachedImage.getHeight();
                    System.out.println("[MediaSource] WebP/Image loaded via ImageIO: " + filePath);
                }
            } catch (Exception e) {
                // Silently move to fallback
            }

            // Strategy 2: Fallback to FFmpeg (VideoDecoder) for WebP if ImageIO fails
            if (cachedImage == null && isWebP) {
                System.out.println("[MediaSource] ImageIO failed for WebP, trying FFmpeg fallback: " + filePath);
                VideoDecoder fallbackDecoder = new VideoDecoder(new File(filePath), 1920, 1080);
                if (fallbackDecoder.init()) {
                    BufferedImage grabbed = fallbackDecoder.getFrame(0);
                    if (grabbed != null) {
                        cachedImage = cloneToARGBPre(grabbed);
                        this.width = cachedImage.getWidth();
                        this.height = cachedImage.getHeight();
                        System.out.println("[MediaSource] WebP loaded via FFmpeg successfully (Cloned)!");
                    } else {
                        System.err.println("[MediaSource] FFmpeg fallback returned NULL frame for: " + filePath);
                    }
                    fallbackDecoder.close();
                } else {
                    System.err.println("[MediaSource] FFmpeg fallback initialization FAILED for: " + filePath);
                }
            }

            // Strategy 3: Standard video path
            if (cachedImage == null && isVideo && videoDecoder != null) {
                cachedImage = videoDecoder.getFrame(0);
            }

            if (cachedImage == null) {
                System.err.println("[MediaSource] CRITICAL: Could not load media file: " + filePath);
            }
        }
        return cachedImage;
    }
}
