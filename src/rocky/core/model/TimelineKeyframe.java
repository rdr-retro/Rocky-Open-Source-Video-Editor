package rocky.core.model;

/**
 * Represents a point in time where a specific frame of the source media
 * is mapped to a specific frame of the clip on the timeline.
 * PURE MODEL: Agnostic to UI framework.
 */
public class TimelineKeyframe {
    private long clipFrame; // Position relative to clip start (0 to clip.duration)
    private long sourceFrame; // Position in the source file (0 to media.duration)
    private ClipTransform transform;

    public TimelineKeyframe(long clipFrame, long sourceFrame) {
        this.clipFrame = clipFrame;
        this.sourceFrame = sourceFrame;
        this.transform = new ClipTransform();
    }

    public TimelineKeyframe(long clipFrame, long sourceFrame, ClipTransform transform) {
        this.clipFrame = clipFrame;
        this.sourceFrame = sourceFrame;
        this.transform = new ClipTransform(transform);
    }

    public TimelineKeyframe copy() {
        return new TimelineKeyframe(this.clipFrame, this.sourceFrame, this.transform);
    }

    public ClipTransform getTransform() {
        return transform;
    }

    public void setTransform(ClipTransform t) {
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
