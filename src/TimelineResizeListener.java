import java.awt.event.ComponentAdapter;
import java.awt.event.ComponentEvent;
import javax.swing.JScrollBar;
import rocky.ui.timeline.TimelinePanel;

public class TimelineResizeListener extends ComponentAdapter {
    private final TimelinePanel timeline;
    private final JScrollBar hScroll;

    public TimelineResizeListener(TimelinePanel timeline, JScrollBar hScroll) {
        this.timeline = timeline;
        this.hScroll = hScroll;
    }

    @Override
    public void componentResized(ComponentEvent e) {
        long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
        long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
        long projectDuration = (long) (timeline.getProjectDuration() * 1000);
        hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
        hScroll.setBlockIncrement((int) visibleDuration);
        hScroll.setUnitIncrement((int) (visibleDuration / 10));
    }
}
