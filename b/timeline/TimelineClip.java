package b.timeline;

import java.awt.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import propiedades.timelinekeyframes.TimelineKeyframe;
import egine.media.ClipMask;

public class TimelineClip {
    private String name;
    private long startFrame;
    private long durationFrames;
    private int trackIndex;
    private String mediaSourceId;
    private long sourceOffsetFrames;
    private List<TimelineKeyframe> timeKeyframes;
    private ClipMask mask;

    // Exact colors from the user's screenshot
    public static final Color HEADER_COLOR = Color.decode("#683539"); // Dark reddish/maroon
    public static final Color BODY_COLOR = Color.decode("#6e3b40"); // Similar body color

    public static final Color AUDIO_HEADER_COLOR = Color.decode("#356839"); // Professional Dark Green
    public static final Color AUDIO_BODY_COLOR = Color.decode("#3b6e40"); // Professional Dark Green
    private ClipTransform transform;

    public TimelineClip(String name, long startFrame, long durationFrames, int trackIndex) {
        this.name = name;
        this.startFrame = startFrame;
        this.durationFrames = durationFrames;
        this.trackIndex = trackIndex;
        this.mediaSourceId = ""; // Default empty
        this.sourceOffsetFrames = 0;
        this.transform = new ClipTransform();
        this.timeKeyframes = new ArrayList<>();
        // Default 1:1 keyframes
        this.timeKeyframes.add(new TimelineKeyframe(0, 0));
        this.timeKeyframes.add(new TimelineKeyframe(durationFrames, durationFrames));
        this.mask = new ClipMask();
    }

    public ClipMask getMask() {
        return mask;
    }

    public void setMask(ClipMask mask) {
        this.mask = mask;
    }

    public List<TimelineKeyframe> getTimeKeyframes() {
        return timeKeyframes;
    }

    public long getSourceFrameAt(long clipFrame) {
        if (timeKeyframes.isEmpty()) {
            return sourceOffsetFrames + clipFrame;
        }

        // Sort keyframes just in case
        timeKeyframes.sort(Comparator.comparingLong(TimelineKeyframe::getClipFrame));

        // Find the bounding keyframes
        TimelineKeyframe left = null;
        TimelineKeyframe right = null;

        for (TimelineKeyframe k : timeKeyframes) {
            if (k.getClipFrame() <= clipFrame) {
                left = k;
            } else {
                right = k;
                break;
            }
        }

        if (left == null)
            return timeKeyframes.get(0).getSourceFrame();
        if (right == null)
            return left.getSourceFrame();

        // Linear interpolation
        double t = (double) (clipFrame - left.getClipFrame()) / (right.getClipFrame() - left.getClipFrame());
        return left.getSourceFrame() + Math.round(t * (right.getSourceFrame() - left.getSourceFrame()));
    }

    public ClipTransform getTransform() {
        return transform;
    }

    public void setTransform(ClipTransform t) {
        this.transform = t;
    }

    public String getMediaSourceId() {
        return mediaSourceId;
    }

    public void setMediaSourceId(String id) {
        this.mediaSourceId = id;
    }

    public long getSourceOffsetFrames() {
        return sourceOffsetFrames;
    }

    public void setSourceOffsetFrames(long offset) {
        this.sourceOffsetFrames = offset;
    }

    public String getName() {
        return name;
    }

    public long getStartFrame() {
        return startFrame;
    }

    public long getDurationFrames() {
        return durationFrames;
    }

    public int getTrackIndex() {
        return trackIndex;
    }

    public enum FadeType {
        LINEAR, FAST, SLOW, SMOOTH, SHARP
    }

    private long fadeOutFrames = 0;
    private long fadeInFrames = 0;
    private FadeType fadeOutType = FadeType.SMOOTH;
    private FadeType fadeInType = FadeType.SMOOTH;

    public void setStartFrame(long startFrame) {
        this.startFrame = startFrame;
    }

    public void setTrackIndex(int trackIndex) {
        this.trackIndex = trackIndex;
    }

    public void setDurationFrames(long durationFrames) {
        this.durationFrames = durationFrames;
    }

    public long getFadeOutFrames() {
        return fadeOutFrames;
    }

    public void setFadeOutFrames(long f) {
        this.fadeOutFrames = f;
    }

    public long getFadeInFrames() {
        return fadeInFrames;
    }

    public void setFadeInFrames(long f) {
        this.fadeInFrames = f;
    }

    public FadeType getFadeOutType() {
        return fadeOutType;
    }

    public void setFadeOutType(FadeType t) {
        this.fadeOutType = t;
    }

    public FadeType getFadeInType() {
        return fadeInType;
    }

    public void setFadeInType(FadeType t) {
        this.fadeInType = t;
    }

    public static double getOpacity(FadeType type, double t, boolean isFadeIn) {
        if (t < 0)
            t = 0;
        if (t > 1)
            t = 1;

        double val = t;

        switch (type) {
            case LINEAR:
                val = t;
                break;
            case FAST:
                val = Math.pow(t, 0.25);
                break;
            case SLOW:
                val = Math.pow(t, 4.0);
                break;
            case SMOOTH:
                val = t * t * (3 - 2 * t);
                break;
            case SHARP:
                val = 0.5 * (Math.sin(Math.PI * (t - 0.5)) + 1);
                break;
        }

        if (isFadeIn)
            return val;
        else
            return 1.0 - val;
    }
}
