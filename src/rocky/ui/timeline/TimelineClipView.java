package rocky.ui.timeline;

import java.awt.Color;
import rocky.core.model.TimelineClip;

/**
 * UI Proxy for TimelineClip.
 * Adds Swing-specific metadata like colors and selection state.
 */
public class TimelineClipView {
    private final TimelineClip model;
    private boolean selected = false;

    // UI Constants moved from legacy TimelineClip
    public static final Color HEADER_COLOR = Color.decode("#4b2a6d"); 
    public static final Color BODY_COLOR = Color.decode("#5e358c"); 

    public static final Color AUDIO_HEADER_COLOR = Color.decode("#3a2a6d"); 
    public static final Color AUDIO_BODY_COLOR = Color.decode("#4a358c"); 

    public TimelineClipView(TimelineClip model) {
        this.model = model;
    }

    public TimelineClip getModel() {
        return model;
    }

    public boolean isSelected() {
        return selected;
    }

    public void setSelected(boolean selected) {
        this.selected = selected;
    }
}
