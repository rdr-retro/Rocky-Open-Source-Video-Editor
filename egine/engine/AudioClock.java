package egine.engine;

/**
 * Provides a master time reference based on audio playback position.
 * Aligning with Sony Vegas "Audio as Master Clock" principle.
 */
public class AudioClock {
    private long baseTimelineFrame = 0;
    private long baseDevicePos = 0;
    private int sampleRate = 48000;
    private int fps = 30;
    private double playbackRate = 1.0;

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
        this.baseTimelineFrame = timelineFrame;
        this.baseDevicePos = currentDevicePos;
    }

    public void setPlaybackRate(double rate, long currentDevicePos) {
        // Update checkpoint before changing rate
        this.baseTimelineFrame = getCurrentTimelineFrame(currentDevicePos);
        this.baseDevicePos = currentDevicePos;
        this.playbackRate = rate;
    }

    public double getPlaybackRate() {
        return playbackRate;
    }

    /**
     * Calculates the current timeline frame based on how many audio frames have been played.
     * @param audioFramesPlayed Number of frames delivered to the audio hardware.
     * @return Current frame on the timeline.
     */
    public long getCurrentTimelineFrame(long audioFramesPlayed) {
        long relativeFrames = audioFramesPlayed - baseDevicePos;
        double seconds = (double) relativeFrames / sampleRate;
        return baseTimelineFrame + (long)(seconds * fps * playbackRate);
    }

    /**
     * Calculates the current time in seconds.
     */
    public double getCurrentTimeInSeconds(long audioFramesPlayed) {
        return (double) getCurrentTimelineFrame(audioFramesPlayed) / fps;
    }
}
