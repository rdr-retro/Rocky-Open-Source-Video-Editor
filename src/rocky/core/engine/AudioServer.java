package rocky.core.engine;

import rocky.core.model.TimelineClip;
import rocky.core.logic.TemporalMath;
import rocky.ui.timeline.TimelinePanel;
import rocky.core.media.MediaPool;
import rocky.core.media.MediaSource;
import rocky.core.audio.MasterSoundPanel;
import java.util.List;
import javax.sound.sampled.*;

/**
 * Handles audio playback and level calculation for meters.
 * Optimized for SMOOTH playback and tight sync using audio as master clock.
 */
public class AudioServer {
    private rocky.core.model.TimelineModel model;
    private MediaPool pool;
    private MasterSoundPanel masterSound;
    private SourceDataLine line;
    private int sampleRate = 48000;
    private double fps = 30.0;

    private Thread audioThread;
    private boolean running = true;
    private long lastTimelineFrame = -1;
    private long samplesWrittenToLine = 0;
    private AudioClock audioClock;

    // Persistent buffers to reduce GC pressure
    private float[] mixedBuffer;
    private byte[] byteBuffer;
    private int samplesPerFrame;

    public AudioServer(rocky.core.model.TimelineModel model, MediaPool pool, MasterSoundPanel masterSound) {
        this.model = model;
        this.pool = pool;
        this.masterSound = masterSound;
        this.audioClock = new AudioClock(sampleRate, fps);
        initAudio();
        startThread();
    }

    public void setProperties(rocky.ui.timeline.ProjectProperties props) {
        int newRate = props.getAudioSampleRate();
        double newFPS = props.getFPS();

        if (newRate != this.sampleRate || Math.abs(newFPS - this.fps) > 0.01) {
            this.sampleRate = newRate;
            this.fps = newFPS;
            this.audioClock = new AudioClock(sampleRate, fps);
            
            // Re-init audio line if sample rate changed
            if (line != null) {
                line.stop();
                line.close();
            }
            initAudio();
        }
    }

    private void initAudio() {
        try {
            AudioFormat format = new AudioFormat(sampleRate, 16, 2, true, false);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, format);
            line = (SourceDataLine) AudioSystem.getLine(info);

            // 1.0s buffer for maximum stability (Increased from 500ms)
            int bufferSize = (int) (sampleRate * 1.0 * format.getFrameSize());
            line.open(format, bufferSize);
            line.start();

            this.samplesPerFrame = (int)((sampleRate / fps) * 2);
            this.mixedBuffer = new float[samplesPerFrame];
            this.byteBuffer = new byte[samplesPerFrame * 2];
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startThread() {
        audioThread = new Thread(() -> {
            long processedTimelineFrame = -1;

            while (running) {
                if (model.getBlueline().isPlaying()) {
                    double rate = model.getBlueline().getPlaybackRate();
                    long currentPlayhead = model.getBlueline().getPlayheadFrame();

                    // If we just started or user jumped (seek)
                    if (processedTimelineFrame == -1 || Math.abs(currentPlayhead - lastTimelineFrame) > 10) {
                        processedTimelineFrame = currentPlayhead;
                        line.flush();
                        audioClock.reset(processedTimelineFrame, line.getLongFramePosition());
                        audioClock.setPlaybackRate(rate, line.getLongFramePosition());

                        // Prime the buffer (Pre-read roughly 250ms for lower latency at high FPS)
                        int primeFrames = (int)(fps * 0.25); 
                        for (int i = 0; i < primeFrames; i++) {
                            processAudioChunk(processedTimelineFrame);
                            if (rate >= 0)
                                processedTimelineFrame++;
                            else
                                processedTimelineFrame--;
                        }
                    } else if (Math.abs(audioClock.getPlaybackRate() - rate) > 0.01) {
                        // Rate changed but no jump: Just update the clock checkpoint
                        audioClock.setPlaybackRate(rate, line.getLongFramePosition());
                    }

                    // Keep the buffer full (Vegas logic: Read Ahead)
                    long deviceFramePos = line.getLongFramePosition();
                    long currentClockFrame = audioClock.getCurrentTimelineFrame(deviceFramePos);

                    // --- STABILITY FIX: Enforce Monotonicity ---
                    // Prevents "micro-rollbacks" caused by audio driver jitter
                    if (lastTimelineFrame != -1) {
                        if (rate > 0 && currentClockFrame < lastTimelineFrame) {
                            currentClockFrame = lastTimelineFrame;
                        } else if (rate < 0 && currentClockFrame > lastTimelineFrame) {
                            currentClockFrame = lastTimelineFrame;
                        }
                    }

                    // Send clock update to UI
                    if (currentClockFrame != lastTimelineFrame) {
                        lastTimelineFrame = currentClockFrame; 
                        final long finalFrame = currentClockFrame; // Local final copy for lambda
                        // Update Model directly
                        model.getBlueline().setPlayheadFrame(finalFrame);
                        // Notify listeners (UI) on EDT
                        javax.swing.SwingUtilities.invokeLater(() -> {
                            model.fireUpdate(); 
                        });
                    }

                    // Fill ahead: up to 250ms (responsive read ahead)
                    int readAhead = (int)(fps * 0.25);
                    boolean needsMore = (rate >= 0) ? (processedTimelineFrame < currentClockFrame + readAhead)
                            : (processedTimelineFrame > currentClockFrame - readAhead);
                    if (needsMore) {
                        processAudioChunk(processedTimelineFrame);
                        if (rate >= 0)
                            processedTimelineFrame++;
                        else
                            processedTimelineFrame--;
                    } else {
                        try {
                            Thread.sleep(2);
                        } catch (Exception e) {
                        }
                    }
                } else {
                    processedTimelineFrame = -1;
                    lastTimelineFrame = -1;
                    masterSound.setLevels(0, 0);
                    if (line != null && line.isActive()) {
                        line.flush();
                    }
                    try {
                        Thread.sleep(10);
                    } catch (Exception e) {
                    }
                }
            }
        }, "AudioEngine-Thread");
        audioThread.setPriority(Thread.MAX_PRIORITY);
        audioThread.start();
    }

    private void processAudioChunk(long frameIndex) {
        double rate = model.getBlueline().getPlaybackRate();
        if (Math.abs(rate) < 0.01) {
            int samplesPerFrame = (int)((sampleRate / fps) * 2);
            playAndMeter(new float[samplesPerFrame]);
            return;
        }

        List<TimelineClip> allClips = model.getClips();
        java.util.Arrays.fill(mixedBuffer, 0);
        boolean anyAudio = false;

        for (TimelineClip clip : allClips) {
            if (frameIndex >= clip.getStartFrame() && frameIndex < (clip.getStartFrame() + clip.getDurationFrames())) {
                boolean isAudio = false;
                if (model.getTrackTypes().size() > clip.getTrackIndex()) {
                    if (model.getTrackTypes().get(clip.getTrackIndex()) == rocky.ui.timeline.TrackControlPanel.TrackType.AUDIO) {
                        isAudio = true;
                    } else {
                        // System.out.println("Track " + clip.getTrackIndex() + " is " + model.getTrackTypes().get(clip.getTrackIndex()));
                    }
                } else {
                     System.out.println("Track Index " + clip.getTrackIndex() + " out of bounds (Size: " + model.getTrackTypes().size() + ")");
                }
                if (!isAudio) {
                    // System.out.println("Skipping clip on track " + clip.getTrackIndex() + " (Not Audio)");
                    continue;
                }

                try {
                    MediaSource source = pool.getSource(clip.getMediaSourceId());
                    if (source != null && source.hasAudio()) {
                        anyAudio = true;

                        double trackVolume = 1.0;
                        long clipLocalFrame = frameIndex - clip.getStartFrame();

                        // Fade In/Out logic
                        if (clipLocalFrame < clip.getFadeInFrames()) {
                            double t = (double) clipLocalFrame / clip.getFadeInFrames();
                            trackVolume = TemporalMath.getFadeValue(clip.getFadeInType(), t, true);
                        } else if (clipLocalFrame > clip.getDurationFrames() - clip.getFadeOutFrames()) {
                            long fadeOutStart = clip.getDurationFrames() - clip.getFadeOutFrames();
                            double t = (double) (clipLocalFrame - fadeOutStart) / clip.getFadeOutFrames();
                            trackVolume = TemporalMath.getFadeValue(clip.getFadeOutType(), t, false);
                        }

                        if (Math.abs(rate - 1.0) < 0.01) {
                            // NORMAL 1.0x SPEED: Use efficient block retrieval
                            long sourceFrame = clip.getSourceOffsetFrames() + clipLocalFrame;
                            short[] samples = source.getAudioSamples(sourceFrame);
                            if (samples != null) {
                                // System.out.println("Processing audio samples for clip " + clip.getName() + " at frame " + frameIndex);
                                for (int i = 0; i < samples.length && i < mixedBuffer.length; i++) {
                                    mixedBuffer[i] += (samples[i] / 32768f) * trackVolume;
                                }
                            } else {
                                // System.out.println("Audio samples NULL for clip " + clip.getName());
                            }
                        } else {
                            // VARIABLE SPEED/REVERSE: Use resampling
                            long startSample = (long) ((clip.getSourceOffsetFrames() + clipLocalFrame)
                                    * (sampleRate / fps));
                            for (int i = 0; i < samplesPerFrame / 2; i++) {
                                double offset = i * rate;
                                long targetSample = startSample + (long) offset;
                                short[] s = source.getAudioSampleAt(targetSample);
                                if (s != null) {
                                    mixedBuffer[i * 2] += (s[0] / 32768f) * trackVolume;
                                    mixedBuffer[i * 2 + 1] += (s[1] / 32768f) * trackVolume;
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    System.out.println("[AudioServer] Error processing clip " + clip.getName() + ": " + e.getMessage());
                }
            }
        }

        if (anyAudio) {
            playAndMeter(mixedBuffer);
        } else {
            playAndMeter(mixedBuffer); // Mixed buffer is already zeros
        }
    }

    private void playAndMeter(float[] mixedSamples) {
        float masterGain = masterSound.getVolume();
        float maxL = 0, maxR = 0;

        for (int i = 0; i < mixedSamples.length; i++) {
            float val = mixedSamples[i] * masterGain;
            float absVal = Math.abs(val);
            if (i % 2 == 0) {
                if (absVal > maxL)
                    maxL = absVal;
            } else {
                if (absVal > maxR)
                    maxR = absVal;
            }

            if (val > 1.0f)
                val = 1.0f;
            else if (val < -1.0f)
                val = -1.0f;

            short s = (short) (val * 32767);
            byteBuffer[i * 2] = (byte) (s & 0xFF);
            byteBuffer[i * 2 + 1] = (byte) (s >> 8);
        }

        if (line != null) {
            try {
                int written = line.write(byteBuffer, 0, byteBuffer.length);
                samplesWrittenToLine += written / 4;
            } catch (Exception e) {
                // Silently handle line errors to keep thread alive
            }
        }
        masterSound.setLevels(maxL, maxR);
    }

    public void processAudio(long targetFrame) {
        // Handled by thread. This method exists for API compatibility.
    }

    public void close() {
        running = false;
        if (line != null) {
            line.stop();
            line.close();
        }
    }
}
