package rocky.core.model;

import rocky.core.plugins.AppliedPlugin;
import rocky.core.structure.IntervalTree;
import rocky.core.blueline.Blueline;
import rocky.ui.timeline.TrackControlPanel;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * pure Data Model for the Timeline.
 * Decouples logic from Swing UI (TimelinePanel).
 */
public class TimelineModel {
    
    // Core Data
    private final List<TimelineClip> clips = Collections.synchronizedList(new ArrayList<>());
    private final IntervalTree<TimelineClip> clipTree = new IntervalTree<>();
    private final Blueline blueline = new Blueline();
    
    // Track Effects (Chain per track)
    private final Map<Integer, List<AppliedPlugin>> trackEffects = new ConcurrentHashMap<>();
    
    // State Tracking
    private final AtomicLong layoutRevision = new AtomicLong(0);

    // Track Configuration
    private List<Integer> trackHeights = new ArrayList<>();
    private final List<TrackControlPanel.TrackType> trackTypes = new java.util.concurrent.CopyOnWriteArrayList<>();

    // Listeners
    public interface ModelListener {
        void onModelUpdated();
    }
    private final List<ModelListener> listeners = new ArrayList<>();

    public TimelineModel() {
    }

    // --- Clip Management ---

    private final java.util.concurrent.locks.ReentrantReadWriteLock treeLock = new java.util.concurrent.locks.ReentrantReadWriteLock();

    public void addClip(TimelineClip clip) {
        clips.add(clip);
        treeLock.writeLock().lock();
        try {
            clipTree.add(clip.getStartFrame(), clip.getStartFrame() + clip.getDurationFrames(), clip);
        } finally {
            treeLock.writeLock().unlock();
        }
        incrementRevision();
        fireUpdate();
    }

    public void removeClip(TimelineClip clip) {
        clips.remove(clip);
        treeLock.writeLock().lock();
        try {
            clipTree.remove(clip.getStartFrame(), clip.getStartFrame() + clip.getDurationFrames(), clip);
        } finally {
             treeLock.writeLock().unlock();
        }
        incrementRevision();
        fireUpdate();
    }

    public void clearClips() {
        clips.clear();
        treeLock.writeLock().lock();
        try {
            clipTree.clear();
        } finally {
            treeLock.writeLock().unlock();
        }
        incrementRevision();
        fireUpdate();
    }
    
    /**
     * Updates a clip's position internally in the tree.
     * Use this when moving/resizing clips to keep the tree consistent.
     */
    public void updateClipPosition(TimelineClip clip, Runnable modification) {
        treeLock.writeLock().lock();
        try {
            // Remove from tree with OLD coordinates
            clipTree.remove(clip.getStartFrame(), clip.getStartFrame() + clip.getDurationFrames(), clip);
            
            // Execute the change properties
            modification.run();
            
            // Re-insert with NEW coordinates
            clipTree.add(clip.getStartFrame(), clip.getStartFrame() + clip.getDurationFrames(), clip);
        } finally {
            treeLock.writeLock().unlock();
        }
        incrementRevision();
    }

    public List<TimelineClip> getClips() {
        synchronized (clips) {
            return new ArrayList<>(clips);
        }
    }
    
    public long getMaxFrame() {
        long max = 0;
        synchronized (clips) {
            for (TimelineClip c : clips) {
                long end = c.getStartFrame() + c.getDurationFrames();
                if (end > max) max = end;
            }
        }
        return max;
    }

    public List<TimelineClip> getClipsAt(long frame) {
        treeLock.readLock().lock();
        try {
            return clipTree.query(frame);
        } finally {
            treeLock.readLock().unlock();
        }
    }

    public IntervalTree<TimelineClip> getClipTree() {
        return clipTree;
    }

    // --- Track Management ---

    public List<Integer> getTrackHeights() {
        return trackHeights;
    }

    public void setTrackHeights(List<Integer> heights) {
        this.trackHeights = heights;
    }
    
    public List<AppliedPlugin> getTrackEffects(int trackIndex) {
        return trackEffects.computeIfAbsent(trackIndex, k -> Collections.synchronizedList(new ArrayList<>()));
    }

    public List<TrackControlPanel.TrackType> getTrackTypes() {
        return trackTypes;
    }
    
    public void addTrackType(TrackControlPanel.TrackType type) {
        trackTypes.add(type);
    }
    
    public void setTrackTypes(List<TrackControlPanel.TrackType> types) {
        trackTypes.clear();
        trackTypes.addAll(types);
    }

    // --- Playhead ---

    public Blueline getBlueline() {
        return blueline;
    }

    // --- Revision ---
    
    public long getLayoutRevision() {
        return layoutRevision.get();
    }
    
    public void incrementRevision() {
        layoutRevision.incrementAndGet();
    }
    
    public void incrementLayoutRevision() {
        incrementRevision();
    }

    // --- Listeners ---
    
    public void addListener(ModelListener l) {
        listeners.add(l);
    }
    
    public void removeListener(ModelListener l) {
        listeners.remove(l);
    }
    
    public void fireUpdate() {
        for (ModelListener l : listeners) {
            l.onModelUpdated();
        }
    }
}
