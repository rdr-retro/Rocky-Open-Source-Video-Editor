package rocky.core.media;

import java.io.File;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;

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

    public MediaSource(String id, String filePath) {
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
                       lower.endsWith(".ogg") || lower.endsWith(".flac");
        
        if (isVideo) {
            this.videoDecoder = new VideoDecoder(new File(filePath), 1920, 1080);
            if (this.videoDecoder.init()) {
                this.totalFrames = this.videoDecoder.getTotalFrames();
                this.width = 1920; 
                this.height = 1080;
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

    public String getId() { return id; }
    public String getFilePath() { return filePath; }
    public long getTotalFrames() { return totalFrames; }
    public int getWidth() { return width; }
    public int getHeight() { return height; }
    public boolean isVideo() { return isVideo; }
    public boolean isAudio() { return isAudio; }

    public boolean hasAudio() {
        if (isAudio) return true;
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
        return new short[]{0, 0};
    }

    private BufferedImage cloneImage(BufferedImage src) {
        if (src == null) return null;
        // BGR24 in FFmpeg fits perfectly with TYPE_INT_RGB (stored as BGR in LE memory)
        BufferedImage dest = new BufferedImage(src.getWidth(), src.getHeight(), BufferedImage.TYPE_INT_RGB);
        java.awt.Graphics2D g = dest.createGraphics();
        g.drawImage(src, 0, 0, null);
        g.dispose();
        return dest;
    }

    public BufferedImage getFrame(long index) {
        if (isVideo && videoDecoder != null) {
            long finalIndex;
            if (filePath.toLowerCase().endsWith(".gif") && totalFrames > 0) {
                // Looping for GIFs
                finalIndex = index % totalFrames;
            } else {
                // Freeze-frame for standard videos
                finalIndex = Math.min(index, totalFrames - 1);
            }
            return videoDecoder.getFrame(finalIndex);
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
                System.out.println("[MediaSource] ImageIO could not read WebP, trying FFmpeg fallback: " + filePath);
                VideoDecoder fallbackDecoder = new VideoDecoder(new File(filePath), 1920, 1080);
                if (fallbackDecoder.init()) {
                    BufferedImage grabbed = fallbackDecoder.getFrame(0);
                    if (grabbed != null) {
                        cachedImage = cloneImage(grabbed);
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
