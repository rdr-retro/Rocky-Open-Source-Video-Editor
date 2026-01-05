package rocky.core.engine;

import java.util.concurrent.CopyOnWriteArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Global controller for Playback Isolation Mode.
 * Prioritizes CPU and Disk resources for the Video Decoder by suspending
 * non-essential background tasks during playback.
 */
public class PlaybackIsolation {
    private static final PlaybackIsolation INSTANCE = new PlaybackIsolation();
    private volatile boolean playbackActive = false;
    private final List<Consumer<Boolean>> listeners = new CopyOnWriteArrayList<>();

    private PlaybackIsolation() {}

    public static PlaybackIsolation getInstance() {
        return INSTANCE;
    }

    public boolean isPlaybackActive() {
        return playbackActive;
    }

    public void setPlaybackActive(boolean active) {
        if (this.playbackActive != active) {
            this.playbackActive = active;
            System.out.println("[PlaybackIsolation] Mode changed to: " + (active ? "ACTIVE (Background tasks paused)" : "INACTIVE (Resuming background tasks)"));
            notifyListeners(active);
        }
    }

    public void addListener(Consumer<Boolean> listener) {
        listeners.add(listener);
    }

    private void notifyListeners(boolean active) {
        for (Consumer<Boolean> listener : listeners) {
            listener.accept(active);
        }
    }
}
