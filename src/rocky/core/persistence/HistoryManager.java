package rocky.core.persistence;

import rocky.ui.timeline.TimelinePanel;
import rocky.ui.timeline.ProjectProperties;
import rocky.ui.timeline.SidebarPanel;
import rocky.core.media.MediaPool;
import java.util.Stack;
import java.util.List;

/**
 * Handles Undo/Redo operations by storing snapshots of the project state.
 */
public class HistoryManager {
    // Basic implementation using snapshots would require a way to serialize/deserialize 
    // the state or a deep copy. For now, we provide the required methods to fix compilation.
    
    private Stack<String> undoStack = new Stack<>();
    private Stack<String> redoStack = new Stack<>();
    private volatile String currentState = null; // Added volatile
    
    // Background thread for serialization to keep EDT fluid
    private final java.util.concurrent.ExecutorService historyExecutor = java.util.concurrent.Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "History-Serializer");
        t.setPriority(Thread.MIN_PRIORITY);
        return t;
    });

    public void pushState(TimelinePanel timeline, ProjectProperties props, MediaPool pool) {
        // 1. Snapshot critical data on EDT (Fast)
        List<rocky.core.model.TimelineClip> clipsSnapshot = timeline.getClips();
        List<Integer> trackHeights = timeline.getTrackHeights();
        List<rocky.ui.timeline.TrackControlPanel.TrackType> trackTypes = timeline.getTrackTypes();
        
        // 2. Offload serialization to background thread
        historyExecutor.submit(() -> {
            // PLAYBACK ISOLATION: Defer state capture if playing
            while (rocky.core.engine.PlaybackIsolation.getInstance().isPlaybackActive()) {
                try { Thread.sleep(500); } catch (InterruptedException e) { break; }
            }

            String state = ProjectManager.serializeProject(clipsSnapshot, props, pool, trackHeights, trackTypes);
            if (state.equals(currentState)) return;
            
            if (currentState != null) {
                undoStack.push(currentState);
            }
            currentState = state;
            redoStack.clear();
            System.out.println("HistoryManager [ASYNC]: State pushed. Undo size: " + undoStack.size() + ", Redo cleared.");
        });
    }

    public void undo(TimelinePanel timeline, ProjectProperties props, MediaPool pool, SidebarPanel sidebar) {
        if (undoStack.isEmpty()) {
            System.out.println("HistoryManager: Nothing to undo");
            return;
        }
        
        redoStack.push(currentState);
        currentState = undoStack.pop();
        
        ProjectManager.deserializeProject(timeline, props, pool, sidebar, currentState);
        System.out.println("HistoryManager: Undo performed. Undo size: " + undoStack.size());
    }

    public void redo(TimelinePanel timeline, ProjectProperties props, MediaPool pool, SidebarPanel sidebar) {
        if (redoStack.isEmpty()) {
            System.out.println("HistoryManager: Nothing to redo");
            return;
        }
        
        undoStack.push(currentState);
        currentState = redoStack.pop();
        
        ProjectManager.deserializeProject(timeline, props, pool, sidebar, currentState);
        System.out.println("HistoryManager: Redo performed. Redo size: " + undoStack.size());
    }
}
