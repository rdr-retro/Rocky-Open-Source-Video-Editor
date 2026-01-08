package rocky.app;

import rocky.ui.timeline.TimelinePanel;
import rocky.ui.timeline.TimelineRuler;
import rocky.ui.viewer.VisualizerPanel;
import rocky.core.engine.FrameServer;
import rocky.core.engine.AudioServer;
import rocky.ui.timeline.SidebarPanel;
import javax.swing.JScrollBar;

public class MainTimelineListener implements TimelinePanel.TimelineListener {
    private final SidebarPanel sidebar;
    private final VisualizerPanel visualizer;
    private final FrameServer frameServer;
    private final AudioServer audioServer;
    private final TimelinePanel timeline;
    private final TimelineRuler ruler;
    private final JScrollBar hScroll;

    public MainTimelineListener(SidebarPanel sidebar, VisualizerPanel visualizer, 
                              FrameServer frameServer, AudioServer audioServer,
                              TimelinePanel timeline, TimelineRuler ruler, JScrollBar hScroll) {
        this.sidebar = sidebar;
        this.visualizer = visualizer;
        this.frameServer = frameServer;
        this.audioServer = audioServer;
        this.timeline = timeline;
        this.ruler = ruler;
        this.hScroll = hScroll;
    }

    @Override
    public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
        sidebar.setTimecode(timecode);
        visualizer.setFrameNumber(frame);
        frameServer.processFrame(time, force);
        audioServer.processAudio(frame);
    }

    @Override
    public void onTimelineUpdated() {
        ruler.repaint();
        long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
        long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
        long projectDuration = (long) (timeline.getProjectDuration() * 1000);
        hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
        hScroll.setBlockIncrement((int) visibleDuration);
        hScroll.setUnitIncrement((int) (visibleDuration / 10));
    }

    @Override
    public void onTimelineStructureChanged() {
        // Invalidate cache only when clips are moved/deleted to prevent ghost images
        frameServer.invalidateCache();
        frameServer.processFrame(timeline.getPlayheadTime(), true);
    }
}
