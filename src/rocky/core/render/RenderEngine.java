package rocky.core.render;

import rocky.core.model.TimelineClip;
import rocky.core.logic.TemporalMath;
import rocky.ui.timeline.TimelinePanel;
import rocky.core.engine.FrameServer;
import rocky.core.media.MediaSource;
import rocky.core.media.MediaPool;
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
                rocky.ui.timeline.ProjectProperties props = frameServer.getProperties();
                // FFmpeg yuv420p requires even dimensions
                int width = props.getProjectWidth();
                if (width % 2 != 0)
                    width--;
                int height = props.getProjectHeight();
                if (height % 2 != 0)
                    height--;

                double fps = props.getFPS();

                System.out.println("[RenderEngine] Starting render: " + width + "x" + height + " @ " + fps + " fps");

                // Determine duration from timeline based on actual content
                long rawTotalFrames = frameServer.getModel().getMaxFrame();
                final long totalFrames = rawTotalFrames <= 0 ? (long) fps : rawTotalFrames;

                // 1. SYNC PROJECT SETTINGS TO ALL SOURCES (Ensure audio speed is correct)
                for (MediaSource ms : frameServer.getMediaPool().getAllSources().values()) {
                    ms.setProjectSettings(fps, props.getAudioSampleRate());
                }

                // 2. RENDER AUDIO TO TEMP WAV
                renderAudioToWav(tempAudioFile, totalFrames, props);

                // 2. RENDER VIDEO AND MUX WITH TEMP AUDIO
                String[] ffmpegCmd = {
                        "ffmpeg", "-y",
                        "-f", "rawvideo",
                        "-pixel_format", "bgra",
                        "-video_size", width + "x" + height,
                        "-r", String.valueOf(fps),
                        "-i", "-",
                        "-i", tempAudioFile.getAbsolutePath(),
                        "-c:v", "libx264",
                        "-pix_fmt", "yuv420p",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        outputFile.getAbsolutePath()
                };

                ProcessBuilder pb = new ProcessBuilder(ffmpegCmd);
                pb.redirectErrorStream(true);
                final Process p = pb.start();
                process = p;

                final StringBuilder ffmpegOutput = new StringBuilder();
                Thread loggerThread = new Thread(() -> {
                    try (java.io.BufferedReader r = new java.io.BufferedReader(
                            new java.io.InputStreamReader(p.getInputStream()))) {
                        String L;
                        while ((L = r.readLine()) != null) {
                            ffmpegOutput.append(L).append("\n");
                            if (L.contains("Error"))
                                System.err.println("[FFmpeg] " + L);
                        }
                    } catch (Exception e) {
                    }
                });
                loggerThread.start();

                OutputStream os = process.getOutputStream();
                BufferedImage blackFrame = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

                // Reuse buffer to avoid OOM/GC pressure on 4K
                ByteBuffer reusableBuffer = ByteBuffer.allocate(width * height * 4);
                reusableBuffer.order(ByteOrder.LITTLE_ENDIAN);

                // Parallel Frame Prefetching for Render
                final int numWorkers = Math.max(2, Runtime.getRuntime().availableProcessors() - 1);
                java.util.concurrent.ExecutorService renderPool = java.util.concurrent.Executors
                        .newFixedThreadPool(numWorkers);
                java.util.concurrent.BlockingQueue<java.util.concurrent.Future<BufferedImage>> frameQueue = new java.util.concurrent.LinkedBlockingQueue<>(
                        numWorkers * 2);

                final int finalW = width;
                final int finalH = height;

                // Producer thread
                new Thread(() -> {
                    try {
                        for (long f = 0; f < totalFrames; f++) {
                            final long frameIdx = f;
                            frameQueue.put(renderPool.submit(() -> {
                                // CRITICAL: Always forceFullRes = true for Rendering
                                // This ensures Proxies and Visor Scale are IGNORED.
                                // We always render from the original source file at max quality.
                                BufferedImage frame = frameServer.getFrameAt(frameIdx, true);
                                if (frame == null)
                                    return blackFrame;

                                // Direct conversion to expected size if needed
                                if (frame.getWidth() != finalW || frame.getHeight() != finalH) {
                                    BufferedImage scaled = new BufferedImage(finalW, finalH,
                                            BufferedImage.TYPE_INT_ARGB);
                                    java.awt.Graphics2D g = scaled.createGraphics();
                                    g.drawImage(frame, 0, 0, finalW, finalH, null);
                                    g.dispose();
                                    return scaled;
                                }
                                return frame;
                            }));
                        }
                    } catch (InterruptedException e) {
                    }
                }).start();

                for (long f = 0; f < totalFrames; f++) {
                    BufferedImage finalFrame = frameQueue.take().get();

                    int[] pixels = ((DataBufferInt) finalFrame.getRaster().getDataBuffer()).getData();
                    reusableBuffer.clear();
                    reusableBuffer.asIntBuffer().put(pixels);

                    try {
                        os.write(reusableBuffer.array());
                        if (f % 30 == 0)
                            os.flush(); // Flush less often
                    } catch (java.io.IOException ioe) {
                        System.err.println("[RenderEngine] Broken pipe detected at frame " + f);
                        throw new Exception("Render pipe broken. FFmpeg details:\n" + ffmpegOutput.toString());
                    }

                    if (listener != null) {
                        final int percent = (int) (f * 100 / totalFrames);
                        SwingUtilities.invokeLater(() -> listener.onProgress(percent));
                    }
                }

                renderPool.shutdownNow();
                os.close();
                int exitCode = process.waitFor();
                loggerThread.join(2000);

                if (listener != null) {
                    if (exitCode == 0)
                        listener.onComplete();
                    else
                        listener.onError("FFmpeg error (code " + exitCode + "). Log:\n" + ffmpegOutput.toString());
                }

            } catch (Exception e) {
                e.printStackTrace();
                if (listener != null) {
                    String msg = e.getMessage();
                    if (msg == null || msg.isEmpty())
                        msg = "Error desconocido durante el renderizado.";
                    listener.onError(msg);
                }
            } finally {
                if (process != null)
                    process.destroy();
                if (tempAudioFile.exists())
                    tempAudioFile.delete();
            }
        }).start();
    }

    private void renderAudioToWav(File wavFile, long totalFrames, rocky.ui.timeline.ProjectProperties props)
            throws Exception {
        int sampleRate = props.getAudioSampleRate();
        double fps = props.getFPS();
        int channels = props.getAudioChannels();
        int framesPerProjectFrame = (int) (sampleRate / fps);
        javax.sound.sampled.AudioFormat format = new javax.sound.sampled.AudioFormat(sampleRate, 16, channels, true,
                false);

        long totalSamples = (long) ((double) totalFrames * sampleRate / fps);
        java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();

        long samplesWritten = 0;
        for (long f = 0; f < totalFrames; f++) {
            // Jitter-aware sample count for this specific frame
            long nextCumulativeSample = (long) ((double) (f + 1) * sampleRate / fps);
            int samplesNeeded = (int) (nextCumulativeSample - samplesWritten);

            float[] mixed = mixFrameAudio(f, samplesNeeded, props);
            for (float val : mixed) {
                // Clipping
                if (val > 1.0f)
                    val = 1.0f;
                else if (val < -1.0f)
                    val = -1.0f;

                short s = (short) (val * 32767);
                baos.write((byte) (s & 0xFF));
                baos.write((byte) (s >> 8));
            }
            samplesWritten += samplesNeeded;
        }

        byte[] audioData = baos.toByteArray();
        java.io.ByteArrayInputStream bais = new java.io.ByteArrayInputStream(audioData);
        javax.sound.sampled.AudioInputStream ais = new javax.sound.sampled.AudioInputStream(bais, format,
                audioData.length / (channels * 2));
        javax.sound.sampled.AudioSystem.write(ais, javax.sound.sampled.AudioFileFormat.Type.WAVE, wavFile);
    }

    private float[] mixFrameAudio(long frameIndex, int samplesNeeded, rocky.ui.timeline.ProjectProperties props) {
        rocky.core.model.TimelineModel model = frameServer.getModel();
        java.util.List<TimelineClip> allClips = model.getClips();
        int sampleRate = props.getAudioSampleRate();
        int channels = props.getAudioChannels();
        int samplesToGenerate = samplesNeeded * channels;
        float[] mixedBuffer = new float[samplesToGenerate];

        for (TimelineClip clip : allClips) {
            if (frameIndex >= clip.getStartFrame() && frameIndex < (clip.getStartFrame() + clip.getDurationFrames())) {
                boolean isAudio = false;
                if (model.getTrackTypes().size() > clip.getTrackIndex()) {
                    if (model.getTrackTypes().get(clip.getTrackIndex()) == rocky.ui.timeline.TrackControlPanel.TrackType.AUDIO) {
                        isAudio = true;
                    }
                }
                if (!isAudio) {
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
                            double t = (double) clipLocalFrame / clip.getFadeInFrames();
                            trackVolume = TemporalMath.getFadeValue(clip.getFadeInType(), t, true);
                        } else if (clipLocalFrame > clip.getDurationFrames() - clip.getFadeOutFrames()) {
                            long fadeOutStart = clip.getDurationFrames() - clip.getFadeOutFrames();
                            double t = (double) (clipLocalFrame - fadeOutStart) / clip.getFadeOutFrames();
                            trackVolume = TemporalMath.getFadeValue(clip.getFadeOutType(), t, false);
                        }

                        for (int i = 0; i < samples.length && i < mixedBuffer.length; i++) {
                            mixedBuffer[i] += (float) ((samples[i] / 32768f) * trackVolume);
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
