package rocky.app;

import java.awt.KeyEventDispatcher;
import java.awt.event.KeyEvent;
import rocky.core.persistence.HistoryManager;
import rocky.ui.timeline.TimelinePanel;
import rocky.ui.timeline.ProjectProperties;
import rocky.core.media.MediaPool;
import rocky.ui.timeline.SidebarPanel;

public class MainUndoRedoDispatcher implements KeyEventDispatcher {
    private final HistoryManager history;
    private final TimelinePanel timeline;
    private final ProjectProperties projectProps;
    private final MediaPool mediaPool;
    private final SidebarPanel sidebar;
    
    public MainUndoRedoDispatcher(HistoryManager history, TimelinePanel timeline, 
                                ProjectProperties projectProps, MediaPool mediaPool, SidebarPanel sidebar) {
        this.history = history;
        this.timeline = timeline;
        this.projectProps = projectProps;
        this.mediaPool = mediaPool;
        this.sidebar = sidebar;
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent e) {
        if (e.getID() == KeyEvent.KEY_PRESSED) {
            boolean ctrl = (e.getModifiersEx()
                    & (System.getProperty("os.name").contains("Mac") ? KeyEvent.META_DOWN_MASK
                            : KeyEvent.CTRL_DOWN_MASK)) != 0;
            if (ctrl) {
                if (e.getKeyCode() == KeyEvent.VK_Z) {
                    if (e.isShiftDown()) {
                        history.redo(timeline, projectProps, mediaPool, sidebar);
                    } else {
                        history.undo(timeline, projectProps, mediaPool, sidebar);
                    }
                    timeline.repaint();
                    return true;
                } else if (e.getKeyCode() == KeyEvent.VK_Y) {
                    history.redo(timeline, projectProps, mediaPool, sidebar);
                    timeline.repaint();
                    return true;
                }
            }
        }
        return false;
    }
}
