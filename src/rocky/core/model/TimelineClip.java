package rocky.core.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import rocky.core.media.ClipMask;

/**
 * Pure data model representing a clip on the timeline.
 * Agnostic to rendering engines (Swing, OpenGL, etc).
 */
public class TimelineClip {
    private volatile String name;
    private volatile long startFrame;
    private volatile long durationFrames;
    private volatile int trackIndex;
    private volatile String mediaSourceId;
    private volatile long sourceOffsetFrames;
    private volatile ClipTransform transform;
    private final List<TimelineKeyframe> timeKeyframes;
    private volatile ClipMask mask;
    private volatile double startOpacity = 1.0;
    private volatile double endOpacity = 1.0;
    
    private long fadeOutFrames = 0;
    private long fadeInFrames = 0;
    private FadeType fadeOutType = FadeType.SMOOTH;
    private FadeType fadeInType = FadeType.SMOOTH;

    public enum FadeType {
        LINEAR, FAST, SLOW, SMOOTH, SHARP
    }

    public TimelineClip(String name, long startFrame, long durationFrames, int trackIndex) {
        this.name = name;
        this.startFrame = startFrame;
        this.durationFrames = durationFrames;
        this.trackIndex = trackIndex;
        this.mediaSourceId = ""; 
        this.sourceOffsetFrames = 0;
        this.transform = new ClipTransform();
        this.timeKeyframes = Collections.synchronizedList(new ArrayList<>());
        this.mask = new ClipMask();
    }

    // Getters / Setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public long getStartFrame() { return startFrame; }
    public void setStartFrame(long startFrame) { this.startFrame = startFrame; }
    
    public long getDurationFrames() { return durationFrames; }
    public void setDurationFrames(long durationFrames) { this.durationFrames = durationFrames; }
    
    public int getTrackIndex() { return trackIndex; }
    public void setTrackIndex(int trackIndex) { this.trackIndex = trackIndex; }
    
    public String getMediaSourceId() { return mediaSourceId; }
    public void setMediaSourceId(String id) { this.mediaSourceId = id; }
    
    public long getSourceOffsetFrames() { return sourceOffsetFrames; }
    public void setSourceOffsetFrames(long offset) { this.sourceOffsetFrames = offset; }
    
    public ClipTransform getTransform() { return transform; }
    public void setTransform(ClipTransform t) { this.transform = t; }
    
    public List<TimelineKeyframe> getTimeKeyframes() { return timeKeyframes; }
    
    public ClipMask getMask() { return mask; }
    public void setMask(ClipMask mask) { this.mask = mask; }
    
    public double getStartOpacity() { return startOpacity; }
    public void setStartOpacity(double opacity) { this.startOpacity = Math.max(0.0, Math.min(1.0, opacity)); }
    
    public double getEndOpacity() { return endOpacity; }
    public void setEndOpacity(double opacity) { this.endOpacity = Math.max(0.0, Math.min(1.0, opacity)); }
    
    public long getFadeOutFrames() { return fadeOutFrames; }
    public void setFadeOutFrames(long f) { this.fadeOutFrames = f; }
    
    public long getFadeInFrames() { return fadeInFrames; }
    public void setFadeInFrames(long f) { this.fadeInFrames = f; }
    
    public FadeType getFadeOutType() { return fadeOutType; }
    public void setFadeOutType(FadeType t) { this.fadeOutType = t; }
    
    public FadeType getFadeInType() { return fadeInType; }
    public void setFadeInType(FadeType t) { this.fadeInType = t; }

    public void addKeyframe(TimelineKeyframe k) {
        synchronized(timeKeyframes) {
            timeKeyframes.add(k);
            sortKeyframes();
        }
    }

    public void sortKeyframes() {
        synchronized(timeKeyframes) {
            timeKeyframes.sort(java.util.Comparator.comparingLong(TimelineKeyframe::getClipFrame));
        }
    }

    public TimelineClip copy() {
        TimelineClip clone = new TimelineClip(this.name, this.startFrame, this.durationFrames, this.trackIndex);
        clone.mediaSourceId = this.mediaSourceId;
        clone.sourceOffsetFrames = this.sourceOffsetFrames;
        clone.transform = new ClipTransform(this.transform);
        clone.mask = (this.mask != null) ? this.mask.copy() : new ClipMask();
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
