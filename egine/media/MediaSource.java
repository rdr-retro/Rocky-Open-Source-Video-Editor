package egine.media;

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
                       lower.endsWith(".webm") || lower.endsWith(".flv");
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
            return audioDecoder.getAudioSamples(index, 1);
        }
        return null;
    }

    public BufferedImage getFrame(long index) {
        if (isVideo && videoDecoder != null) {
            return videoDecoder.getFrame(index);
        }
        return getOrLoadImage();
    }

    public BufferedImage getOrLoadImage() {
        if (cachedImage == null) {
            if (isVideo && videoDecoder != null) {
                cachedImage = videoDecoder.getFrame(0);
            } else {
                try {
                    cachedImage = ImageIO.read(new File(filePath));
                    if (cachedImage != null) {
                        this.width = cachedImage.getWidth();
                        this.height = cachedImage.getHeight();
                    }
                } catch (Exception e) {
                    System.err.println("Error loading image: " + filePath);
                }
            }
        }
        return cachedImage;
    }
}
