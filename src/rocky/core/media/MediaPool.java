package rocky.core.media;

import java.util.HashMap;
import java.util.Map;

/**
 * A central registry for all MediaSource objects in the project.
 */
public class MediaPool {
    private Map<String, MediaSource> sources = new HashMap<>();

    public void addSource(MediaSource source) {
        sources.put(source.getId(), source);
    }

    public MediaSource getSource(String id) {
        return sources.get(id);
    }

    public Map<String, MediaSource> getAllSources() {
        return sources;
    }

    public void clear() {
        sources.clear();
    }
}
