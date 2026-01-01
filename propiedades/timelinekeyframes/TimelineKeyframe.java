package propiedades.timelinekeyframes;

/**
 * Represents a point in time where a specific frame of the source media
 * is mapped to a specific frame of the clip on the timeline.
 */
public class TimelineKeyframe {
    private long clipFrame; // Position relative to clip start (0 to clip.duration)
    private long sourceFrame; // Position in the source file (0 to media.duration)
    private b.timeline.ClipTransform transform;

    public TimelineKeyframe(long clipFrame, long sourceFrame) {
        this.clipFrame = clipFrame;
        this.sourceFrame = sourceFrame;
        this.transform = new b.timeline.ClipTransform();
    }

    public TimelineKeyframe(long clipFrame, long sourceFrame, b.timeline.ClipTransform transform) {
        this.clipFrame = clipFrame;
        this.sourceFrame = sourceFrame;
        this.transform = new b.timeline.ClipTransform(transform);
    }

    public b.timeline.ClipTransform getTransform() {
        return transform;
    }

    public void setTransform(b.timeline.ClipTransform t) {
        this.transform = t;
    }

    public long getClipFrame() {
        return clipFrame;
    }

    public void setClipFrame(long f) {
        this.clipFrame = f;
    }

    public long getSourceFrame() {
        return sourceFrame;
    }

    public void setSourceFrame(long f) {
        this.sourceFrame = f;
    }
}
