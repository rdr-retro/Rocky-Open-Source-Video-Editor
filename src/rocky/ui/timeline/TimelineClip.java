package rocky.ui.timeline;

import java.awt.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import rocky.ui.keyframes.TimelineKeyframe;
import rocky.core.media.ClipMask;

/**
 * Represents a clip on the timeline.
 */
public class TimelineClip {
    private String name;
    private long startFrame;
    private long durationFrames;
    private int trackIndex;
    private String mediaSourceId;
    private long sourceOffsetFrames;
    private ClipTransform transform;
    private final List<TimelineKeyframe> timeKeyframes;
    private ClipMask mask;
    private double startOpacity = 1.0;
    private double endOpacity = 1.0;

    // Exact colors from the user's screenshot
    public static final Color HEADER_COLOR = Color.decode("#4b2a6d"); 
    public static final Color BODY_COLOR = Color.decode("#5e358c"); 

    public static final Color AUDIO_HEADER_COLOR = Color.decode("#3a2a6d"); 
    public static final Color AUDIO_BODY_COLOR = Color.decode("#4a358c"); 

    public TimelineClip(String name, long startFrame, long durationFrames, int trackIndex) {
        this.name = name;
        this.startFrame = startFrame;
        this.durationFrames = durationFrames;
        this.trackIndex = trackIndex;
        this.mediaSourceId = ""; // Default empty
        this.sourceOffsetFrames = 0;
        this.transform = new ClipTransform();
        this.timeKeyframes = Collections.synchronizedList(new ArrayList<>());
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

    public void addKeyframe(TimelineKeyframe k) {
        synchronized(timeKeyframes) {
            timeKeyframes.add(k);
            sortKeyframes();
        }
    }

    public void sortKeyframes() {
        synchronized(timeKeyframes) {
            timeKeyframes.sort(Comparator.comparingLong(TimelineKeyframe::getClipFrame));
        }
    }

    public long getSourceFrameAt(long clipFrame) {
        synchronized(timeKeyframes) {
            if (timeKeyframes.isEmpty()) {
                return sourceOffsetFrames + clipFrame;
            }

            // Find the bounding keyframes (Assumes already sorted for performance)
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
    }

    public ClipTransform getInterpolatedTransform(long clipFrame) {
        synchronized (timeKeyframes) {
            if (timeKeyframes.isEmpty()) {
                return transform;
            }

            // Assumes already sorted for performance
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
                return new ClipTransform(timeKeyframes.get(0).getTransform());
            if (right == null)
                return new ClipTransform(left.getTransform());

            // Interpolate
            double t = (double) (clipFrame - left.getClipFrame()) / (right.getClipFrame() - left.getClipFrame());

            ClipTransform lt = left.getTransform();
            ClipTransform rt = right.getTransform();

            ClipTransform result = new ClipTransform();
            result.setX(lt.getX() + t * (rt.getX() - lt.getX()));
            result.setY(lt.getY() + t * (rt.getY() - lt.getY()));
            result.setScaleX(lt.getScaleX() + t * (rt.getScaleX() - lt.getScaleX()));
            result.setScaleY(lt.getScaleY() + t * (rt.getScaleY() - lt.getScaleY()));
            result.setRotation(lt.getRotation() + t * (rt.getRotation() - lt.getRotation()));
            result.setAnchorX(lt.getAnchorX() + t * (rt.getAnchorX() - lt.getAnchorX()));
            result.setAnchorY(lt.getAnchorY() + t * (rt.getAnchorY() - lt.getAnchorY()));

            return result;
        }
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

    public double getStartOpacity() {
        return startOpacity;
    }

    public void setStartOpacity(double opacity) {
        this.startOpacity = Math.max(0.0, Math.min(1.0, opacity));
    }

    public double getEndOpacity() {
        return endOpacity;
    }

    public void setEndOpacity(double opacity) {
        this.endOpacity = Math.max(0.0, Math.min(1.0, opacity));
    }

    public double getOpacityAt(long clipFrame) {
        double progress = (double) clipFrame / durationFrames;
        if (progress < 0) progress = 0;
        if (progress > 1) progress = 1;

        double baseOpacityAtFrame = startOpacity + progress * (endOpacity - startOpacity);
        double opacity = baseOpacityAtFrame;

        // Fade In
        if (clipFrame < fadeInFrames) {
            double t = (double) clipFrame / fadeInFrames;
            opacity *= getOpacity(fadeInType, t, true);
        }
        // Fade Out
        else if (clipFrame > durationFrames - fadeOutFrames) {
            long fadeOutStart = durationFrames - fadeOutFrames;
            double t = (double) (clipFrame - fadeOutStart) / fadeOutFrames;
            opacity *= getOpacity(fadeOutType, t, false);
        }

        return opacity;
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

    public TimelineClip copy() {
        TimelineClip clone = new TimelineClip(this.name, this.startFrame, this.durationFrames, this.trackIndex);
        clone.mediaSourceId = this.mediaSourceId;
        clone.sourceOffsetFrames = this.sourceOffsetFrames;
        clone.transform = new ClipTransform(this.transform);
        clone.mask = (this.mask != null) ? this.mask.copy() : new rocky.core.media.ClipMask();
        clone.startOpacity = this.startOpacity;
        clone.endOpacity = this.endOpacity;
        clone.fadeInFrames = this.fadeInFrames;
        clone.fadeOutFrames = this.fadeOutFrames;
        clone.fadeInType = this.fadeInType;
        clone.fadeOutType = this.fadeOutType;
        
        synchronized(this.timeKeyframes) {
            for (TimelineKeyframe k : this.timeKeyframes) {
                clone.timeKeyframes.add(k.copy());
            }
        }
        return clone;
    }
}
