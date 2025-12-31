package egine.render;

import b.timeline.TimelinePanel;
import egine.engine.FrameServer;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import javax.swing.SwingUtilities;

/**
 * Handles the rendering process by piping frames to FFmpeg.
 */
public class RenderEngine {
    private FrameServer frameServer;
    private int width;
    private int height;
    private int fps = 30;

    public RenderEngine(FrameServer frameServer, int width, int height) {
        this.frameServer = frameServer;
        this.width = width;
        this.height = height;
    }

    public void render(File outputFile, RenderProgressListener listener) {
        new Thread(() -> {
            Process process = null;
            try {
                // Determine duration from timeline based on actual content
                long totalFrames = frameServer.getTimeline().getContentDurationFrames();
                if (totalFrames <= 0) totalFrames = fps; // Default 1 second if empty
                
                // FFmpeg command: pipe from stdin (raw video) to mp4
                String[] ffmpegCmd = {
                    "ffmpeg",
                    "-y",                 // Overwrite
                    "-f", "rawvideo",     // Input format
                    "-pixel_format", "bgra", 
                    "-video_size", width + "x" + height,
                    "-r", String.valueOf(fps),
                    "-i", "-",            // Input from pipe
                    "-c:v", "libx264",    // Video codec
                    "-pix_fmt", "yuv420p",// Compatibility
                    "-crf", "18",         // High quality
                    outputFile.getAbsolutePath()
                };

                ProcessBuilder pb = new ProcessBuilder(ffmpegCmd);
                pb.redirectErrorStream(true);
                process = pb.start();
                
                OutputStream os = process.getOutputStream();
                
                BufferedImage blackFrame = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                
                for (long f = 0; f < totalFrames; f++) {
                    BufferedImage frame = frameServer.getFrameAt(f);
                    if (frame == null) frame = blackFrame;
                    
                    // We need to ensure the frame is the right size and type
                    BufferedImage resizedFrame = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                    java.awt.Graphics2D g = resizedFrame.createGraphics();
                    g.drawImage(frame, 0, 0, width, height, null);
                    g.dispose();
                    
                    // Extract raw bytes (BGRA)
                    int[] pixels = ((DataBufferInt) resizedFrame.getRaster().getDataBuffer()).getData();
                    ByteBuffer buffer = ByteBuffer.allocate(pixels.length * 4);
                    buffer.order(ByteOrder.LITTLE_ENDIAN);
                    buffer.asIntBuffer().put(pixels);
                    
                    os.write(buffer.array());
                    os.flush();
                    
                    if (listener != null) {
                        listener.onProgress((int) (f * 100 / totalFrames));
                    }
                }
                
                os.close();
                int exitCode = process.waitFor();
                
                if (listener != null) {
                    if (exitCode == 0) listener.onComplete();
                    else listener.onError("FFmpeg exited with error code: " + exitCode);
                }
                
            } catch (Exception e) {
                e.printStackTrace();
                if (listener != null) listener.onError(e.getMessage());
            } finally {
                if (process != null) process.destroy();
            }
        }).start();
    }

    public interface RenderProgressListener {
        void onProgress(int percentage);
        void onComplete();
        void onError(String message);
    }
}
