package rocky.core.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import rocky.core.media.ClipMask;
import rocky.core.plugins.AppliedPlugin;

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
    
    private volatile AppliedPlugin mediaGenerator;
    private volatile AppliedPlugin fadeInTransition;
    private volatile AppliedPlugin fadeOutTransition;
    
    private final List<AppliedPlugin> appliedEffects = Collections.synchronizedList(new ArrayList<>());

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

    public AppliedPlugin getMediaGenerator() { return mediaGenerator; }
    public void setMediaGenerator(AppliedPlugin g) { this.mediaGenerator = g; }

    public AppliedPlugin getFadeInTransition() { return fadeInTransition; }
    public void setFadeInTransition(AppliedPlugin t) { this.fadeInTransition = t; }
    
    public AppliedPlugin getFadeOutTransition() { return fadeOutTransition; }
    public void setFadeOutTransition(AppliedPlugin t) { this.fadeOutTransition = t; }

    public List<AppliedPlugin> getAppliedEffects() { return appliedEffects; }
    
    public void addEffect(AppliedPlugin effect) {
        appliedEffects.add(effect);
    }

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
        clone.mediaGenerator = (this.mediaGenerator != null) ? new AppliedPlugin(this.mediaGenerator.getPluginName()) : null;
        if (clone.mediaGenerator != null) clone.mediaGenerator.getParameters().putAll(this.mediaGenerator.getParameters());
        clone.fadeInTransition = (this.fadeInTransition != null) ? new AppliedPlugin(this.fadeInTransition.getPluginName()) : null;
        if (clone.fadeInTransition != null) clone.fadeInTransition.getParameters().putAll(this.fadeInTransition.getParameters());
        clone.fadeOutTransition = (this.fadeOutTransition != null) ? new AppliedPlugin(this.fadeOutTransition.getPluginName()) : null;
        if (clone.fadeOutTransition != null) clone.fadeOutTransition.getParameters().putAll(this.fadeOutTransition.getParameters());
        
        synchronized(this.timeKeyframes) {
            for (TimelineKeyframe k : this.timeKeyframes) {
                clone.timeKeyframes.add(k.copy());
            }
        }
        
        synchronized(this.appliedEffects) {
            for (AppliedPlugin effect : this.appliedEffects) {
                // Note: We'll need a way to copy AppliedPlugin if it's mutable
                // For now, let's assume it has a copy constructor or just copy the map
                AppliedPlugin copy = new AppliedPlugin(effect.getPluginName());
                copy.getParameters().putAll(effect.getParameters());
                clone.appliedEffects.add(copy);
            }
        }
        return clone;
    }
}
