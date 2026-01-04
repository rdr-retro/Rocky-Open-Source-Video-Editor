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
    private int rotation = 0;
    private int width;
    private int height;
    private double scaleFactor = 1.0;
    private long lastFrameNumber = -2; 
    private double videoFPS = 30.0;

    public VideoDecoder(File file, int width, int height) {
        this.videoFile = file;
        this.width = width;
        this.height = height;
        this.converter = new Java2DFrameConverter();
    }

    public void setScaleFactor(double scale) {
        this.scaleFactor = scale;
    }

    public void setVideoFPS(double fps) {
        this.videoFPS = fps;
    }

    public boolean init() {
        try {
            System.out.println("[VideoDecoder] Initializing for: " + videoFile.getName() + " (Scale: " + scaleFactor + ")");
            // Use DecoderPool to acquire a grabber (reused or new)
            grabber = DecoderPool.acquire(videoFile);
            
            // Enhanced probing for complex MOV/MP4 containers
            grabber.setOption("probesize", "10485760"); // 10MB
            grabber.setOption("analyzeduration", "10000000"); // 10s

            // Cross-Platform Hardware Acceleration Detection
            String os = System.getProperty("os.name").toLowerCase();
            String lowerName = videoFile.getName().toLowerCase();
            boolean isWebP = lowerName.endsWith(".webp");
            boolean isGIF = lowerName.endsWith(".gif");
            boolean isMOV = lowerName.endsWith(".mov");

            // Hardware Acceleration Detection
            if (!isWebP && !isGIF) {
                if (os.contains("mac")) {
                    grabber.setVideoOption("hwaccel", "videotoolbox");
                } else if (os.contains("win")) {
                    grabber.setVideoOption("hwaccel", "dxva2"); 
                } else if (os.contains("nix") || os.contains("nux")) {
                    grabber.setVideoOption("hwaccel", "vaapi");
                }
            } else if (isMOV) {
                // For non-mac platforms, MOV might still need software mode for safety
                // but on Mac we prioritize VideoToolbox.
                grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24);
            }
            
            try {
                grabber.start();
                
                // --- NATIVE SCALING OPTIMIZATION ---
                int nativeW = grabber.getImageWidth();
                int nativeH = grabber.getImageHeight();
                
                if (scaleFactor < 1.0 && !isGIF && !isWebP) {
                    int targetW = (int) Math.max(1, nativeW * scaleFactor);
                    int targetH = (int) Math.max(1, nativeH * scaleFactor);
                    System.out.println("[VideoDecoder] Applying NATIVE SCALING: " + nativeW + "x" + nativeH + " -> " + targetW + "x" + targetH);
                    
                    grabber.stop();
                    grabber.setImageWidth(targetW);
                    grabber.setImageHeight(targetH);
                    // Re-apply options before restart
                    if (isMOV) grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24);
                    else if (!isWebP && !isGIF) { // Re-apply hwaccel if it was set
                        if (os.contains("mac")) {
                            grabber.setVideoOption("hwaccel", "videotoolbox");
                        } else if (os.contains("win")) {
                            grabber.setVideoOption("hwaccel", "dxva2"); 
                        } else if (os.contains("nix") || os.contains("nux")) {
                            grabber.setVideoOption("hwaccel", "vaapi");
                        }
                    }
                    grabber.start();
                }

                System.out.println("[VideoDecoder] Started successfully with codec: " + grabber.getVideoCodecName());
            } catch (Exception e) {
                System.err.println("[VideoDecoder] Initial start failed: " + e.getMessage());
                System.err.println("[VideoDecoder] Attempting software fallback...");
                
                if (grabber != null) {
                    try { grabber.stop(); } catch(Exception ex) {}
                    try { grabber.release(); } catch(Exception ex) {}
                }
                
                // Software fallback with universal settings
                // We don't use pool for fallback creation to ensure fresh state, 
                // but we could. For safety, let's just use new here and NOT pool fallback grabbers
                // OR we can just create a new one. 
                // Since fallback is rare and critical, simple is better.
                if (grabber != null) {
                     // If the pooled grabber failed, release it (or maybe discard it? Release puts it back).
                     // Ideally we should discard broken grabbers. 
                     // But DecoderPool.release assumes valid. 
                     // Let's just destroy it.
                     try { grabber.stop(); grabber.release(); } catch(Exception ex) {}
                }
                grabber = new FFmpegFrameGrabber(videoFile);
                grabber.setOption("probesize", "10485760");
                grabber.setOption("analyzeduration", "10000000");
                grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24);
                grabber.setOption("threads", "auto");
                
                try {
                    grabber.start();
                    // Apply scaling to fallback too if needed
                    int nativeW = grabber.getImageWidth();
                    int nativeH = grabber.getImageHeight();
                    if (scaleFactor < 1.0) {
                        int targetW = (int) Math.max(1, nativeW * scaleFactor);
                        int targetH = (int) Math.max(1, nativeH * scaleFactor);
                        System.out.println("[VideoDecoder] Applying NATIVE SCALING (Fallback): " + nativeW + "x" + nativeH + " -> " + targetW + "x" + targetH);
                        grabber.stop();
                        grabber.setImageWidth(targetW);
                        grabber.setImageHeight(targetH);
                        grabber.setPixelFormat(avutil.AV_PIX_FMT_BGR24); // Ensure pixel format is set for restart
                        grabber.setOption("threads", "auto"); // Ensure threads option is set for restart
                        grabber.start();
                    }
                    System.out.println("[VideoDecoder] Software fallback SUCCESS");
                } catch (Exception e2) {
                    System.err.println("[VideoDecoder] CRITICAL: All decoding attempts failed");
                    e2.printStackTrace();
                    return false;
                }
            }

            // --- DETECT ACTUAL DIMENSIONS AND ROTATION ---
            int codedW = grabber.getImageWidth();
            int codedH = grabber.getImageHeight();
            
            // Robust rotation detection via multiple possible metadata keys
            String rotMeta = grabber.getVideoMetadata("rotate");
            if (rotMeta == null) rotMeta = grabber.getVideoMetadata("orientation");
            if (rotMeta == null) rotMeta = grabber.getVideoMetadata("ROTATION");
            
            // Some cameras (Sony/Panasonic) might use different keys or the format metadata
            if (rotMeta == null && grabber.getMetadata() != null) {
                rotMeta = grabber.getMetadata().get("rotate");
                if (rotMeta == null) rotMeta = grabber.getMetadata().get("orientation");
            }

            if (rotMeta != null) {
                try {
                    // Remove " degrees" or other non-numeric suffix if present
                    String cleanRot = rotMeta.replaceAll("[^0-9\\-]", "");
                    this.rotation = Integer.parseInt(cleanRot);
                } catch (Exception e) {
                    this.rotation = 0;
                }
            } else {
                this.rotation = 0;
            }
            
            System.out.println("[VideoDecoder] Detected Metadata Rotation: " + rotMeta + " -> " + this.rotation);

            if ((rotation == 90 || rotation == 270 || rotation == -90 || rotation == -270) && codedW > codedH) {
                // If rotated 90/270 AND coded dimensions are horizontal, swap them
                this.width = codedH;
                this.height = codedW;
            } else {
                this.width = codedW;
                this.height = codedH;
            }

            System.out.println("[VideoDecoder] Final Logical Dimensions: " + width + "x" + height);
            
            return true;
        } catch (Exception e) {
            System.err.println("[VideoDecoder] Failed to init: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }

    public int getWidth() { return width; }
    public int getHeight() { return height; }

    public boolean hasAudio() {
        if (grabber == null) return false;
        return grabber.getAudioStream() != -1 || grabber.getAudioChannels() > 0;
    }

    public synchronized BufferedImage getFrame(long frameNumber) {
        try {
            if (grabber == null) return null;
            
            // Refresh LRU status in the pool so we are not evicted during long playback
            DecoderPool.touch(videoFile.getAbsolutePath());
            
            // Fuzzy Sequential Logic
            // If we are close enough (e.g. within 5 frames forward), just read through
            // This avoids flushing the decoder pipeline which happens on seek/timestamp change
            boolean isSequential = (frameNumber == lastFrameNumber + 1);
            boolean isCloseEnough = (frameNumber > lastFrameNumber && frameNumber <= lastFrameNumber + 5);
            
            if (!isSequential) {
                if (isCloseEnough) {
                    // Consume intervening frames
                    int framesToSkip = (int)(frameNumber - lastFrameNumber - 1);
                    for (int i = 0; i < framesToSkip; i++) {
                        grabber.grabImage(); // Discard
                    }
                } else {
                    // Long Seek
                    // Optimize for MP4/MOV: setVideoFrameNumber is precise and often faster
                    String fmt = grabber.getFormat();
                    if (fmt != null && (fmt.contains("mp4") || fmt.contains("mov"))) {
                        grabber.setVideoFrameNumber((int)frameNumber);
                    } else {
                        // Fallback to timestamp for others
                        long timestamp = Math.round((frameNumber / videoFPS) * 1000000);
                        grabber.setTimestamp(timestamp);
                    }
                }
            }
            
            Frame frame = grabber.grabImage();
            
            if (frame == null && frameNumber < 5) {
                grabber.setTimestamp(0);
                frame = grabber.grabImage();
            }

            lastFrameNumber = frameNumber;
            
            if (frame != null && frame.image != null) {
                BufferedImage raw = converter.getBufferedImage(frame);
                
                // --- AUTO-ROTATION DETECTION ---
                // If the grabbed frame dimensions already match our logical (target) 
                // dimensions, it means the decoder (Hardware Accel) already applied 
                // the rotation for us.
                if (raw.getWidth() == this.width && raw.getHeight() == this.height) {
                    return raw;
                }

                if (rotation == 0) return raw;

                // Handle Manual Rotation Logic
                BufferedImage rotated = new BufferedImage(width, height, raw.getType());
                Graphics2D g2 = rotated.createGraphics();
                
                // We need to handle the rotation based on what we calculated in init()
                // but double check if we are already rotated (some grabbers do it, some don't)
                if (rotation == 90 || rotation == -270) {
                    g2.translate(width, 0);
                    g2.rotate(Math.toRadians(90));
                } else if (rotation == 180 || rotation == -180) {
                    g2.translate(width, height);
                    g2.rotate(Math.toRadians(180));
                } else if (rotation == 270 || rotation == -90) {
                    g2.translate(0, height);
                    g2.rotate(Math.toRadians(270));
                }
                
                g2.drawImage(raw, 0, 0, null);
                g2.dispose();
                return rotated;
            }
        } catch (Exception e) {
            System.err.println("[VideoDecoder] Error grabbing frame " + frameNumber + ": " + e.getMessage());
        }
        return null;
    }

    public long getTotalFrames() {
        if (grabber == null) return 0;
        double durationSecs = grabber.getLengthInTime() / 1000000.0;
        return Math.round(durationSecs * videoFPS);
    }

    public void close() {
        try {
            if (converter != null) converter.close();
            if (grabber != null) {
                // Return to pool instead of releasing completely
                // Note: The pool decides if it keeps it open or not.
                DecoderPool.release(videoFile, grabber);
                grabber = null; // Detach
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
