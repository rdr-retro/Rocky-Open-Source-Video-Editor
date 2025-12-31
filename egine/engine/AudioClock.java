package egine.engine;

/**
 * Provides a master time reference based on audio playback position.
 * Aligning with Sony Vegas "Audio as Master Clock" principle.
 */
public class AudioClock {
    private long startFrameOffset = 0;
    private long baseDeviceFramePos = 0;
    private int sampleRate = 48000;
    private int fps = 30;

    public AudioClock(int sampleRate, int fps) {
        this.sampleRate = sampleRate;
        this.fps = fps;
    }

    /**
     * Resets the clock to a new timeline position.
     * @param timelineFrame The frame on the timeline where playback starts.
     * @param currentDevicePos The current absolute position of the audio line.
     */
    public void reset(long timelineFrame, long currentDevicePos) {
        this.startFrameOffset = timelineFrame;
        this.baseDeviceFramePos = currentDevicePos;
    }

    /**
     * Calculates the current timeline frame based on how many audio frames have been played.
     * @param audioFramesPlayed Number of frames delivered to the audio hardware.
     * @return Current frame on the timeline.
     */
    public long getCurrentTimelineFrame(long audioFramesPlayed) {
        long relativeFrames = audioFramesPlayed - baseDeviceFramePos;
        double seconds = (double) relativeFrames / sampleRate;
        return startFrameOffset + (long)(seconds * fps);
    }

    /**
     * Calculates the current time in seconds.
     */
    public double getCurrentTimeInSeconds(long audioFramesPlayed) {
        return (double) startFrameOffset / fps + (double) audioFramesPlayed / sampleRate;
    }
}
