package rocky.core.media;

import java.awt.image.BufferedImage;
import java.awt.Graphics2D;
import java.io.File;
import org.bytedeco.javacv.*;
import org.bytedeco.ffmpeg.global.avutil;

/**
 * Logical part extracted from user's code to handle video decoding
 * optimized for Apple M4.
 */
public class VideoDecoder {
    private File videoFile;
    private FFmpegFrameGrabber grabber;
    private Java2DFrameConverter converter;
    private int width;
    private int height;
    private long lastFrameNumber = -2; 
    private double videoFPS = 30.0;

    public VideoDecoder(File file, int width, int height) {
        this.videoFile = file;
        this.width = width;
        this.height = height;
        this.converter = new Java2DFrameConverter();
    }

    public boolean init() {
        try {
            System.out.println("[VideoDecoder] Initializing for: " + videoFile.getName());
            grabber = new FFmpegFrameGrabber(videoFile);
            
            // Light probing for faster startup
            grabber.setOption("probesize", "1048576"); // 1MB
            grabber.setOption("analyzeduration", "1000000"); // 1s

            // Cross-Platform Hardware Acceleration Detection
            String os = System.getProperty("os.name").toLowerCase();
            boolean isWebP = videoFile.getName().toLowerCase().endsWith(".webp");

            if (!isWebP) {
                if (os.contains("mac")) {
                    grabber.setVideoOption("hwaccel", "videotoolbox");
                    System.out.println("[VideoDecoder] Using Hardware Accel: VideoToolbox (macOS)");
                } else if (os.contains("win")) {
                    grabber.setVideoOption("hwaccel", "dxva2"); // Or d3d11va
                    System.out.println("[VideoDecoder] Using Hardware Accel: DXVA2 (Windows)");
                } else if (os.contains("nix") || os.contains("nux")) {
                    grabber.setVideoOption("hwaccel", "vaapi");
                    System.out.println("[VideoDecoder] Using Hardware Accel: VAAPI (Linux)");
                }
            } else {
                System.out.println("[VideoDecoder] WebP detected: Disabling Hardware Accel for compatibility.");
            }
            
            // Reverting to BGR24 as it matches Java's default pixel order for INT_RGB on Little Endian
            grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24); 
            grabber.start();

            int audioStream = grabber.getAudioStream();
            int audioChannels = grabber.getAudioChannels();
            
            this.videoFPS = grabber.getFrameRate();
            if (this.videoFPS <= 0) this.videoFPS = 30.0;

            System.out.println("[VideoDecoder] Started. Audio Stream: " + audioStream + 
                               ", Channels: " + audioChannels + 
                               ", Video Stream: " + grabber.getVideoStream() +
                               ", FPS: " + videoFPS);
            
            return true;
        } catch (Exception e) {
            System.err.println("[VideoDecoder] Failed to init: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }

    public boolean hasAudio() {
        if (grabber == null) return false;
        // Robust check: any of these indicate an audio presence
        return grabber.getAudioStream() != -1 || 
               grabber.getAudioChannels() > 0;
    }

    public BufferedImage getFrame(long frameNumber) {
        try {
            if (grabber == null) return null;
            
            // Optimization: If it's the next frame, don't seek! 
            if (frameNumber != lastFrameNumber + 1 && frameNumber != 0) {
                long timestamp = (long)((frameNumber / videoFPS) * 1000000);
                grabber.setTimestamp(timestamp);
            }
            
            Frame frame = grabber.grabImage();
            lastFrameNumber = frameNumber;
            
            if (frame != null && frame.image != null) {
                return converter.getBufferedImage(frame);
            }
        } catch (Exception e) {
            System.err.println("[VideoDecoder] Error grabbing frame " + frameNumber + ": " + e.getMessage());
        }
        return null;
    }

    public long getTotalFrames() {
        if (grabber == null) return 0;
        double durationSecs = grabber.getLengthInTime() / 1000000.0;
        return (long)(durationSecs * videoFPS);
    }

    public void close() {
        try {
            if (converter != null) converter.close();
            if (grabber != null) {
                grabber.stop();
                grabber.release();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
