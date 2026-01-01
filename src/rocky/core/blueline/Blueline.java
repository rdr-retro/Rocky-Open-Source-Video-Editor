package rocky.core.blueline;

import java.awt.*;

/**
 * Handles the logic and state of the playhead (the "blue line").
 * Centralizes playback status and frame position.
 */
public class Blueline {
    private long playheadFrame = 0;
    private long playbackStartFrame = 0;
    private boolean isPlaying = false;
    private final int FPS = 30;
    private final Color PLAYHEAD_COLOR = Color.decode("#54a0ff");
    private double playbackRate = 1.0; // 1.0 = Normal, 2.0 = 2x, -1.0 = Reverse

    public long getPlayheadFrame() {
        return playheadFrame;
    }

    public void setPlayheadFrame(long frame) {
        this.playheadFrame = frame;
    }

    public boolean isPlaying() {
        return isPlaying;
    }

    public void setPlaying(boolean playing) {
        this.isPlaying = playing;
    }

    public double getPlaybackRate() {
        return playbackRate;
    }

    public void setPlaybackRate(double rate) {
        this.playbackRate = rate;
    }

    public void startPlayback() {
        this.playbackStartFrame = playheadFrame;
        this.isPlaying = true;
    }

    public void stopPlayback() {
        this.isPlaying = false;
    }

    public long getPlaybackStartFrame() {
        return playbackStartFrame;
    }

    public Color getColor() {
        return PLAYHEAD_COLOR;
    }

    /**
     * Logic for automatic horizontal scrolling to follow the playhead.
     * @param visibleStartTime Current start time of the view in seconds
     * @param visibleDuration Current duration of the visible area in seconds
     * @return The new suggested visibleStartTime, or -1 if no change is needed
     */
    public double calculateAutoScroll(double visibleStartTime, double visibleDuration) {
        if (!isPlaying) return -1;

        double time = playheadFrame / (double) FPS;
        if (time < visibleStartTime || time > visibleStartTime + visibleDuration) {
            return time; // Suggest jumping to the playhead position
        }
        return -1;
    }

    public String formatTimecode(long frames) {
        long f = frames % FPS;
        long totalSeconds = frames / FPS;
        long s = totalSeconds % 60;
        long m = (totalSeconds / 60) % 60;
        long h = totalSeconds / 3600;
        return String.format("%02d:%02d:%02d;%02d", h, m, s, f);
    }
}
