package egine.engine;

import b.timeline.TimelineClip;
import b.timeline.TimelinePanel;
import egine.media.MediaPool;
import egine.media.MediaSource;
import a.mastersound.MasterSoundPanel;
import java.util.List;
import javax.sound.sampled.*;

/**
 * Handles audio playback and level calculation for meters.
 * Optimized for SMOOTH playback and tight sync using audio as master clock.
 */
public class AudioServer {
    private TimelinePanel timeline;
    private MediaPool pool;
    private MasterSoundPanel masterSound;
    private SourceDataLine line;
    private final int SAMPLE_RATE = 48000;
    private final int FPS = 30;
    
    private Thread audioThread;
    private boolean running = true;
    private long lastTimelineFrame = -1;
    private long samplesWrittenToLine = 0;
    private AudioClock audioClock;

    public AudioServer(TimelinePanel timeline, MediaPool pool, MasterSoundPanel masterSound) {
        this.timeline = timeline;
        this.pool = pool;
        this.masterSound = masterSound;
        this.audioClock = new AudioClock(SAMPLE_RATE, FPS);
        initAudio();
        startThread();
    }

    private void initAudio() {
        try {
            AudioFormat format = new AudioFormat(SAMPLE_RATE, 16, 2, true, true);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, format);
            line = (SourceDataLine) AudioSystem.getLine(info);
            
            // 200ms buffer to absorb jitter (Sony Vegas style "Read Ahead")
            // Smaller buffer = more responsive scrubbing
            int bufferSize = (int) (SAMPLE_RATE * 0.2 * format.getFrameSize());
            line.open(format, bufferSize);
            line.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startThread() {
        audioThread = new Thread(() -> {
            long processedTimelineFrame = -1;

            while (running) {
                if (timeline != null && timeline.isPlaying()) {
                    double rate = timeline.getPlaybackRate();
                    long currentPlayhead = timeline.getPlayheadFrame();
                    
                    // If we just started or user jumped (seek)
                    if (processedTimelineFrame == -1 || Math.abs(currentPlayhead - lastTimelineFrame) > 10) {
                        processedTimelineFrame = currentPlayhead;
                        line.flush();
                        audioClock.reset(processedTimelineFrame, line.getLongFramePosition());
                        audioClock.setPlaybackRate(rate, line.getLongFramePosition());
                        
                        // Prime the buffer (Pre-read roughly 5 frames for lower latency)
                        for (int i = 0; i < 5; i++) {
                            processAudioChunk(processedTimelineFrame);
                            if (rate >= 0) processedTimelineFrame++; else processedTimelineFrame--;
                        }
                    } else if (Math.abs(audioClock.getPlaybackRate() - rate) > 0.01) {
                        // Rate changed but no jump: Just update the clock checkpoint
                        audioClock.setPlaybackRate(rate, line.getLongFramePosition());
                    }

                    // Keep the buffer full (Vegas logic: Read Ahead)
                    long deviceFramePos = line.getLongFramePosition();
                    long currentClockFrame = audioClock.getCurrentTimelineFrame(deviceFramePos);
                    
                    // Send clock update to UI
                    if (currentClockFrame != lastTimelineFrame) {
                        lastTimelineFrame = currentClockFrame;
                        javax.swing.SwingUtilities.invokeLater(() -> {
                            timeline.updatePlayheadFromFrame(currentClockFrame);
                        });
                    }

                    // Fill ahead: up to 10 frames (responsive read ahead)
                    boolean needsMore = (rate >= 0) ? (processedTimelineFrame < currentClockFrame + 10) : (processedTimelineFrame > currentClockFrame - 10);
                    if (needsMore) {
                        processAudioChunk(processedTimelineFrame);
                        if (rate >= 0) processedTimelineFrame++; else processedTimelineFrame--;
                    } else {
                        try { Thread.sleep(2); } catch (Exception e) {}
                    }
                } else {
                    processedTimelineFrame = -1;
                    lastTimelineFrame = -1;
                    masterSound.setLevels(0, 0);
                    try { Thread.sleep(10); } catch (Exception e) {}
                }
            }
        }, "AudioEngine-Thread");
        audioThread.setPriority(Thread.MAX_PRIORITY);
        audioThread.start();
    }

    private void processAudioChunk(long frameIndex) {
        double rate = timeline.getPlaybackRate();
        if (Math.abs(rate) < 0.01) {
            int samplesPerFrame = (SAMPLE_RATE / FPS) * 2;
            playAndMeter(new float[samplesPerFrame]);
            return;
        }

        List<TimelineClip> allClips = timeline.getClips();
        int samplesPerFrame = (SAMPLE_RATE / FPS) * 2;
        float[] mixedBuffer = new float[samplesPerFrame];
        boolean anyAudio = false;

        for (TimelineClip clip : allClips) {
            if (frameIndex >= clip.getStartFrame() && frameIndex < (clip.getStartFrame() + clip.getDurationFrames())) {
                if (timeline.getTrackType(clip.getTrackIndex()) != b.timeline.TrackControlPanel.TrackType.AUDIO) {
                    continue;
                }
                
                MediaSource source = pool.getSource(clip.getMediaSourceId());
                if (source != null && source.hasAudio()) {
                    anyAudio = true;
                    
                    double trackVolume = 1.0;
                    long clipLocalFrame = frameIndex - clip.getStartFrame();
                    
                    // Fade In/Out logic
                    if (clipLocalFrame < clip.getFadeInFrames()) {
                        double t = (double)clipLocalFrame / clip.getFadeInFrames();
                        trackVolume = TimelineClip.getOpacity(clip.getFadeInType(), t, true);
                    } else if (clipLocalFrame > clip.getDurationFrames() - clip.getFadeOutFrames()) {
                        long fadeOutStart = clip.getDurationFrames() - clip.getFadeOutFrames();
                        double t = (double)(clipLocalFrame - fadeOutStart) / clip.getFadeOutFrames();
                        trackVolume = TimelineClip.getOpacity(clip.getFadeOutType(), t, false);
                    }

                    if (Math.abs(rate - 1.0) < 0.01) {
                        // NORMAL 1.0x SPEED: Use efficient block retrieval
                        long sourceFrame = clip.getSourceOffsetFrames() + clipLocalFrame;
                        short[] samples = source.getAudioSamples(sourceFrame);
                        if (samples != null) {
                            for (int i = 0; i < samples.length && i < mixedBuffer.length; i++) {
                                mixedBuffer[i] += (samples[i] / 32768f) * trackVolume;
                            }
                        }
                    } else {
                        // VARIABLE SPEED/REVERSE: Use resampling
                        // Calculate start/end sample positions in source
                        long startSample = (long)((clip.getSourceOffsetFrames() + clipLocalFrame) * (SAMPLE_RATE / (double)FPS));
                        
                        for (int i = 0; i < samplesPerFrame / 2; i++) {
                            // We calculate the sample position relative to the 30fps frame start
                            // This ensures sync even with drifting rates
                            double offset = i * rate;
                            long targetSample = startSample + (long)offset;
                            
                            short[] s = source.getAudioSampleAt(targetSample);
                            if (s != null) {
                                mixedBuffer[i * 2] += (s[0] / 32768f) * trackVolume;
                                mixedBuffer[i * 2 + 1] += (s[1] / 32768f) * trackVolume;
                            }
                        }
                    }
                }
            }
        }

        if (anyAudio) {
            playAndMeter(mixedBuffer);
        } else {
            playAndMeter(new float[samplesPerFrame]);
        }
    }

    private void playAndMeter(float[] mixedSamples) {
        byte[] bytes = new byte[mixedSamples.length * 2];
        float masterGain = masterSound.getVolume();
        float maxL = 0, maxR = 0;
        
        for (int i = 0; i < mixedSamples.length; i++) {
            // Apply Master Gain
            float val = mixedSamples[i] * masterGain;
            
            // Metering (pre-clipping)
            float absVal = Math.abs(val);
            if (i % 2 == 0) { if (absVal > maxL) maxL = absVal; }
            else { if (absVal > maxR) maxR = absVal; }

            // Hard Clipping protection
            if (val > 1.0f) val = 1.0f;
            else if (val < -1.0f) val = -1.0f;
            
            // Convert back to 16-bit PCM
            short s = (short) (val * 32767);
            bytes[i * 2] = (byte) (s >> 8);
            bytes[i * 2 + 1] = (byte) (s & 0xFF);
        }
        
        if (line != null) {
            line.write(bytes, 0, bytes.length);
            samplesWrittenToLine += mixedSamples.length / 2;
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
