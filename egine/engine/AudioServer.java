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
            
            // 500ms buffer to absorb jitter (Sony Vegas style "Read Ahead")
            int bufferSize = (int) (SAMPLE_RATE * 0.5 * format.getFrameSize());
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
                    long currentPlayhead = timeline.getPlayheadFrame();
                    
                    // If we just started or user jumped (seek)
                    // We check if the current playhead is significantly different from what we last set
                    if (processedTimelineFrame == -1 || Math.abs(currentPlayhead - lastTimelineFrame) > 5) {
                        processedTimelineFrame = currentPlayhead;
                        line.flush();
                        audioClock.reset(processedTimelineFrame, line.getLongFramePosition());
                        
                        // Prime the buffer (Pre-read roughly 10 frames)
                        for (int i = 0; i < 10; i++) {
                            processAudioChunk(processedTimelineFrame);
                            processedTimelineFrame++;
                        }
                    }

                    // Keep the buffer full (Vegas logic: Read Ahead)
                    // We check processedTimelineFrame against the actual device clock
                    long deviceFramePos = line.getLongFramePosition();
                    long currentClockFrame = audioClock.getCurrentTimelineFrame(deviceFramePos);
                    
                    // Send clock update to UI
                    if (currentClockFrame != lastTimelineFrame) {
                        lastTimelineFrame = currentClockFrame;
                        javax.swing.SwingUtilities.invokeLater(() -> {
                            timeline.updatePlayheadFromFrame(currentClockFrame);
                        });
                    }

                    // Fill ahead: up to 15 frames (0.5s @ 30fps)
                    if (processedTimelineFrame < currentClockFrame + 15) {
                        processAudioChunk(processedTimelineFrame);
                        processedTimelineFrame++;
                    } else {
                        try { Thread.sleep(5); } catch (Exception e) {}
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
        List<TimelineClip> allClips = timeline.getClips();
        short[] masterBuffer = null;

        for (TimelineClip clip : allClips) {
            if (frameIndex >= clip.getStartFrame() && frameIndex < (clip.getStartFrame() + clip.getDurationFrames())) {
                // Vegas Logic: Only clips on Audio tracks contribute to audio output
                if (timeline.getTrackType(clip.getTrackIndex()) != b.timeline.TrackControlPanel.TrackType.AUDIO) {
                    continue;
                }
                
                MediaSource source = pool.getSource(clip.getMediaSourceId());
                if (source != null && source.hasAudio()) {
                    long sourceFrame = clip.getSourceOffsetFrames() + (frameIndex - clip.getStartFrame());
                    short[] samples = source.getAudioSamples(sourceFrame);
                    if (samples != null) {
                        if (masterBuffer == null) masterBuffer = new short[samples.length];
                        
                        // --- APPLY FADES ---
                        double volume = 1.0;
                        long clipLocalFrame = frameIndex - clip.getStartFrame();
                        
                        // Fade In
                        if (clipLocalFrame < clip.getFadeInFrames()) {
                            double t = (double)clipLocalFrame / clip.getFadeInFrames();
                            volume = TimelineClip.getOpacity(clip.getFadeInType(), t, true);
                        }
                        // Fade Out
                        else if (clipLocalFrame > clip.getDurationFrames() - clip.getFadeOutFrames()) {
                            long fadeOutStart = clip.getDurationFrames() - clip.getFadeOutFrames();
                            double t = (double)(clipLocalFrame - fadeOutStart) / clip.getFadeOutFrames();
                            volume = TimelineClip.getOpacity(clip.getFadeOutType(), t, false);
                        }

                        for (int i = 0; i < samples.length; i++) {
                            masterBuffer[i] += (short)(samples[i] * volume);
                        }
                    }
                }
            }
        }

        if (masterBuffer != null) {
            playAndMeter(masterBuffer);
        } else {
            // Write silence to maintain the clock but don't show levels
            int silentSamples = (SAMPLE_RATE / FPS) * 2;
            playAndMeter(new short[silentSamples]);
            masterSound.setLevels(0, 0);
        }
    }

    private void playAndMeter(short[] samples) {
        byte[] bytes = new byte[samples.length * 2];
        float maxL = 0, maxR = 0;
        
        for (int i = 0; i < samples.length; i++) {
            short s = samples[i];
            float val = Math.abs(s) / 32768f;
            if (i % 2 == 0) { if (val > maxL) maxL = val; }
            else { if (val > maxR) maxR = val; }
            
            bytes[i * 2] = (byte) (s >> 8);
            bytes[i * 2 + 1] = (byte) (s & 0xFF);
        }
        
        if (line != null) {
            line.write(bytes, 0, bytes.length);
            samplesWrittenToLine += samples.length / 2; // samples per channel
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
