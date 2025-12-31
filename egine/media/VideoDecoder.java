package egine.media;

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

            // Hardware Acceleration for Mac (Apple M4)
            grabber.setVideoOption("hwaccel", "videotoolbox");
            
            grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24); 
            grabber.start();

            int audioStream = grabber.getAudioStream();
            int audioChannels = grabber.getAudioChannels();
            
            System.out.println("[VideoDecoder] Started. Audio Stream: " + audioStream + 
                               ", Channels: " + audioChannels + 
                               ", Video Stream: " + grabber.getVideoStream());
            
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
            // Just grab. This is HUGE for performance during playback.
            if (frameNumber != lastFrameNumber + 1) {
                long timestamp = (long)((frameNumber / 30.0) * 1000000);
                grabber.setTimestamp(timestamp);
            }
            
            Frame frame = grabber.grabImage();
            lastFrameNumber = frameNumber;
            
            if (frame != null && frame.image != null) {
                BufferedImage bi = converter.convert(frame);
                if (bi != null) {
                    // Fast clone
                    BufferedImage copy = new BufferedImage(bi.getWidth(), bi.getHeight(), BufferedImage.TYPE_INT_RGB);
                    Graphics2D g = copy.createGraphics();
                    g.drawImage(bi, 0, 0, null);
                    g.dispose();
                    return copy;
                }
            }
        } catch (Exception e) {
            System.err.println("[VideoDecoder] Error grabbing frame " + frameNumber + ": " + e.getMessage());
        }
        return null;
    }

    public long getTotalFrames() {
        if (grabber == null) return 0;
        double durationSecs = grabber.getLengthInTime() / 1000000.0;
        return (long)(durationSecs * 30);
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
