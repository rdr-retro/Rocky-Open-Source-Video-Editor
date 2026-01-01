package propiedades.timelinekeyframes;

/**
 * Represents a point in time where a specific frame of the source media 
 * is mapped to a specific frame of the clip on the timeline.
 */
public class TimelineKeyframe {
    private long clipFrame;   // Position relative to clip start (0 to clip.duration)
    private long sourceFrame; // Position in the source file (0 to media.duration)

    public TimelineKeyframe(long clipFrame, long sourceFrame) {
        this.clipFrame = clipFrame;
        this.sourceFrame = sourceFrame;
    }

    public long getClipFrame() { return clipFrame; }
    public void setClipFrame(long f) { this.clipFrame = f; }

    public long getSourceFrame() { return sourceFrame; }
    public void setSourceFrame(long f) { this.sourceFrame = f; }
}
