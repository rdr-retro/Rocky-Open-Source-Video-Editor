package rocky.core.render;

import rocky.ui.timeline.TimelinePanel;
import rocky.core.engine.FrameServer;
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
    public RenderEngine(FrameServer frameServer) {
        this.frameServer = frameServer;
    }

    public void render(File outputFile, RenderProgressListener listener) {
        new Thread(() -> {
            Process process = null;
            File tempAudioFile = new File(outputFile.getParent(), "temp_audio_" + System.currentTimeMillis() + ".wav");
            try {
                rocky.ui.timeline.ProjectProperties props = frameServer.getTimeline().getProjectProperties();
                int width = props.getProjectWidth();
                int height = props.getProjectHeight();
                double fps = props.getFPS();

                // Determine duration from timeline based on actual content
                long rawTotalFrames = frameServer.getTimeline().getContentDurationFrames();
                final long totalFrames = rawTotalFrames <= 0 ? (long)fps : rawTotalFrames;
                
                // 1. RENDER AUDIO TO TEMP WAV
                renderAudioToWav(tempAudioFile, totalFrames, props);

                // 2. RENDER VIDEO AND MUX WITH TEMP AUDIO
                // FFmpeg command: pipe from stdin (raw video) and temp audio file to mp4
                String[] ffmpegCmd = {
                    "ffmpeg",
                    "-y",                 // Overwrite
                    "-f", "rawvideo",     // Input video format from pipe
                    "-pixel_format", "bgra", 
                    "-video_size", width + "x" + height,
                    "-r", String.valueOf(fps),
                    "-i", "-",            // Input video from pipe
                    "-i", tempAudioFile.getAbsolutePath(), // Input audio from file
                    "-c:v", "libx264",    // Video codec
                    "-pix_fmt", "yuv420p",// Compatibility
                    "-crf", "18",         // High quality
                    "-c:a", "aac",        // Audio codec
                    "-b:a", "192k",       // Audio bitrate
                    "-shortest",          // End when the shortest stream ends
                    outputFile.getAbsolutePath()
                };

                ProcessBuilder pb = new ProcessBuilder(ffmpegCmd);
                pb.redirectErrorStream(true);
                process = pb.start();
                
                OutputStream os = process.getOutputStream();
                BufferedImage blackFrame = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                
                // Parallel Frame Prefetching for Render
                final int numWorkers = Runtime.getRuntime().availableProcessors();
                java.util.concurrent.ExecutorService renderPool = java.util.concurrent.Executors.newFixedThreadPool(numWorkers);
                java.util.concurrent.BlockingQueue<java.util.concurrent.Future<BufferedImage>> frameQueue = 
                    new java.util.concurrent.LinkedBlockingQueue<>(numWorkers * 2);

                // Producer thread
                new Thread(() -> {
                    try {
                        for (long f = 0; f < totalFrames; f++) {
                            final long frameIdx = f;
                            frameQueue.put(renderPool.submit(() -> {
                                BufferedImage frame = frameServer.getFrameAt(frameIdx, true);
                                if (frame == null) return blackFrame;
                                
                                // Direct conversion to expected size if needed
                                if (frame.getWidth() != width || frame.getHeight() != height) {
                                    BufferedImage scaled = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
                                    java.awt.Graphics2D g = scaled.createGraphics();
                                    g.drawImage(frame, 0, 0, width, height, null);
                                    g.dispose();
                                    return scaled;
                                }
                                return frame;
                            }));
                        }
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }).start();

                for (long f = 0; f < totalFrames; f++) {
                    BufferedImage finalFrame = frameQueue.take().get();
                    
                    // Extract raw bytes (BGRA) from the buffered image efficiently
                    int[] pixels = ((DataBufferInt) finalFrame.getRaster().getDataBuffer()).getData();
                    ByteBuffer buffer = ByteBuffer.allocate(pixels.length * 4);
                    buffer.order(ByteOrder.LITTLE_ENDIAN);
                    buffer.asIntBuffer().put(pixels);
                    
                    os.write(buffer.array());
                    os.flush();
                    
                    if (listener != null) {
                        final int percent = (int)(f * 100 / totalFrames);
                        SwingUtilities.invokeLater(() -> listener.onProgress(percent));
                    }
                }
                
                renderPool.shutdown();
                
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
                if (tempAudioFile.exists()) tempAudioFile.delete();
            }
        }).start();
    }

    private void renderAudioToWav(File wavFile, long totalFrames, rocky.ui.timeline.ProjectProperties props) throws Exception {
        int sampleRate = props.getAudioSampleRate();
        double fps = 30.0; // Standardized
        int channels = props.getAudioChannels();
        int framesPerProjectFrame = (int)(sampleRate / fps);
        javax.sound.sampled.AudioFormat format = new javax.sound.sampled.AudioFormat(sampleRate, 16, channels, true, false);
        
        long totalSamples = totalFrames * framesPerProjectFrame;
        java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
        
        for (long f = 0; f < totalFrames; f++) {
            float[] mixed = mixFrameAudio(f);
            for (float val : mixed) {
                // Clipping
                if (val > 1.0f) val = 1.0f;
                else if (val < -1.0f) val = -1.0f;
                
                short s = (short) (val * 32767);
                baos.write((byte) (s & 0xFF));
                baos.write((byte) (s >> 8));
            }
        }
        
        byte[] audioData = baos.toByteArray();
        java.io.ByteArrayInputStream bais = new java.io.ByteArrayInputStream(audioData);
        javax.sound.sampled.AudioInputStream ais = new javax.sound.sampled.AudioInputStream(bais, format, audioData.length / (channels * 2));
        javax.sound.sampled.AudioSystem.write(ais, javax.sound.sampled.AudioFileFormat.Type.WAVE, wavFile);
    }

    private float[] mixFrameAudio(long frameIndex) {
        TimelinePanel timeline = frameServer.getTimeline();
        java.util.List<rocky.ui.timeline.TimelineClip> allClips = timeline.getClips();
        rocky.ui.timeline.ProjectProperties props = timeline.getProjectProperties();
        int sampleRate = props.getAudioSampleRate();
        double fps = 30.0; // Standardized
        int channels = props.getAudioChannels();
        int samplesPerFrame = (int)((sampleRate / fps) * channels);
        float[] mixedBuffer = new float[samplesPerFrame];

        for (rocky.ui.timeline.TimelineClip clip : allClips) {
            if (frameIndex >= clip.getStartFrame() && frameIndex < (clip.getStartFrame() + clip.getDurationFrames())) {
                if (timeline.getTrackType(clip.getTrackIndex()) != rocky.ui.timeline.TrackControlPanel.TrackType.AUDIO) {
                    continue;
                }
                
                rocky.core.media.MediaSource source = frameServer.getMediaPool().getSource(clip.getMediaSourceId());
                if (source != null && source.hasAudio()) {
                    long sourceFrame = clip.getSourceOffsetFrames() + (frameIndex - clip.getStartFrame());
                    short[] samples = source.getAudioSamples(sourceFrame);
                    if (samples != null) {
                        double trackVolume = 1.0;
                        long clipLocalFrame = frameIndex - clip.getStartFrame();
                        
                        // Fades
                        if (clipLocalFrame < clip.getFadeInFrames()) {
                            double t = (double)clipLocalFrame / clip.getFadeInFrames();
                            trackVolume = rocky.ui.timeline.TimelineClip.getOpacity(clip.getFadeInType(), t, true);
                        } else if (clipLocalFrame > clip.getDurationFrames() - clip.getFadeOutFrames()) {
                            long fadeOutStart = clip.getDurationFrames() - clip.getFadeOutFrames();
                            double t = (double)(clipLocalFrame - fadeOutStart) / clip.getFadeOutFrames();
                            trackVolume = rocky.ui.timeline.TimelineClip.getOpacity(clip.getFadeOutType(), t, false);
                        }

                        for (int i = 0; i < samples.length && i < mixedBuffer.length; i++) {
                            mixedBuffer[i] += (float)((samples[i] / 32768f) * trackVolume);
                        }
                    }
                }
            }
        }
        return mixedBuffer;
    }

    public interface RenderProgressListener {
        void onProgress(int percentage);
        void onComplete();
        void onError(String message);
    }
}
