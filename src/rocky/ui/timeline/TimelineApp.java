package rocky.ui.timeline;

import rocky.ui.viewer.VisualizerPanel;
import rocky.core.audio.MasterSoundPanel;
import rocky.core.media.MediaPool;
import rocky.ui.timeline.ProjectProperties;
import rocky.core.persistence.HistoryManager;
import rocky.core.engine.FrameServer;
import rocky.core.engine.AudioServer;
import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import rocky.core.model.TimelineModel;
import java.awt.image.BufferedImage;

public class TimelineApp {
    public static void main(String[] args) {
        // --- PERFORMANCE: Enable Hardware Acceleration ---
        System.setProperty("sun.java2d.metal", "true");   // macOS
        System.setProperty("sun.java2d.opengl", "true");  // Windows/Linux fallback
        System.setProperty("apple.awt.graphics.UseQuartz", "true");
        
        // --- PERFORMANCE: Standardize on ARGB_PRE for UI components ---
        System.setProperty("sun.java2d.uiScale", "1.0"); // Consistent scaling for buffers

        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                e.printStackTrace();
            }

            JFrame frame = new JFrame("Timeline");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setSize(1200, 800); // Increased height for the split view
            frame.setBackground(Color.decode("#1e1e1e"));
            frame.setLayout(new BorderLayout());

            // --- PART B: Timeline Components ---
            MediaPool mediaPool = new MediaPool();
            ProjectProperties projectProps = new ProjectProperties();
            HistoryManager historyManager = new HistoryManager();
            
            SidebarPanel sidebar = new SidebarPanel();
            TimelineModel model = new TimelineModel();
            TimelinePanel timeline = new TimelinePanel(model);
            TimelineRuler ruler = new TimelineRuler(timeline);

            timeline.setMediaPool(mediaPool);
            timeline.setProjectProperties(projectProps);
            timeline.setHistoryManager(historyManager);
            timeline.setSidebar(sidebar);

            sidebar.setOnAddTrack(() -> {
                timeline.setTrackHeights(sidebar.getTrackHeights());
            });

            // --- PART A: Top Section (Visualizer) ---
            JPanel topPanel = new JPanel(new BorderLayout());
            topPanel.setBackground(Color.decode("#1e1e1e"));

            // Left placeholder (e.g. for media library)
            JPanel leftPlaceholder = new JPanel();
            leftPlaceholder.setBackground(Color.decode("#161616"));
            leftPlaceholder.setPreferredSize(new Dimension(300, 0));
            topPanel.add(leftPlaceholder, BorderLayout.WEST);

            // Right Visualizer
            VisualizerPanel visualizer = new VisualizerPanel();
            topPanel.add(visualizer, BorderLayout.CENTER);

            // Master Sound (Far Right)
            MasterSoundPanel masterSound = new MasterSoundPanel();
            topPanel.add(masterSound, BorderLayout.EAST);

            // --- ENGINE SETUP ---
            FrameServer frameServer = new FrameServer(model, mediaPool, visualizer);
            frameServer.setProperties(projectProps);
            
            AudioServer audioServer = new AudioServer(model, mediaPool, masterSound);
            
            // Connect Visualizer to Audio/Video
            visualizer.setOnPlay(timeline::startPlayback);
            visualizer.setOnPause(timeline::pausePlayback);
            visualizer.setOnStop(timeline::stopPlayback);
            visualizer.updateProperties(projectProps);

            // --- LISTENERS ---
            timeline.setTimelineListener(new TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
                    sidebar.setTimecode(timecode);
                    // REAL-TIME UPDATE: Notify FrameServer to render the frame
                    if (frameServer != null) {
                        frameServer.processFrame(time, force);
                    }
                }

                @Override
                public void onTimelineUpdated() {
                    ruler.repaint();
                }

                @Override
                public void onTimelineStructureChanged() {
                    // FORCE RE-RENDER on state update (clip add/delete/split)
                    if (frameServer != null) {
                        frameServer.invalidateCache();
                        frameServer.processFrame(timeline.getPlayheadTime(), true);
                    }
                }
            });

            JScrollPane scrollPane = new JScrollPane(timeline);
            scrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
            scrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
            scrollPane.setBorder(null);

            JViewport rowViewport = new JViewport();
            rowViewport.setView(sidebar.getSidebarContent());
            scrollPane.setRowHeader(rowViewport);
            scrollPane.setColumnHeaderView(ruler);
            scrollPane.setCorner(JScrollPane.UPPER_LEFT_CORNER, sidebar.getHeaderPanel());

            JPanel centerContainer = new JPanel(new BorderLayout());
            centerContainer.add(scrollPane, BorderLayout.CENTER);

            JPanel scrollbarPanel = new JPanel(new BorderLayout());
            scrollbarPanel.setBackground(Color.decode("#1e1e1e"));

            JPanel sidebarSpacer = new JPanel();
            sidebarSpacer.setPreferredSize(new Dimension(250, 0));
            sidebarSpacer.setBackground(Color.decode("#1e1e1e"));
            scrollbarPanel.add(sidebarSpacer, BorderLayout.WEST);

            JScrollBar hScroll = new JScrollBar(JScrollBar.HORIZONTAL);
            scrollbarPanel.add(hScroll, BorderLayout.CENTER);

            hScroll.addAdjustmentListener(e -> {
                double time = e.getValue() / 1000.0;
                if (Math.abs(timeline.getVisibleStartTime() - time) > 0.05) {
                    timeline.setHorizontalScroll(time);
                    ruler.repaint();
                }
            });
            centerContainer.add(scrollbarPanel, BorderLayout.SOUTH);

            // Update the TimelineUpdated logic to use hScroll
            timeline.addTimelineListener(new TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {}

                @Override
                public void onTimelineUpdated() {
                    long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
                    long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
                    long projectDuration = (long) (timeline.getProjectDuration() * 1000);
                    hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
                    hScroll.setBlockIncrement((int) visibleDuration);
                    hScroll.setUnitIncrement((int) (visibleDuration / 10));
                }

                @Override
                public void onTimelineStructureChanged() {
                }
            });

            timeline.addComponentListener(new ComponentAdapter() {
                @Override
                public void componentResized(ComponentEvent e) {
                    long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
                    long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
                    long projectDuration = (long) (timeline.getProjectDuration() * 1000);
                    hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
                    hScroll.setBlockIncrement((int) visibleDuration);
                    hScroll.setUnitIncrement((int) (visibleDuration / 10));
                }
            });

            // --- MAIN LAYOUT: JSplitPane ---
            JSplitPane mainSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, topPanel, centerContainer);
            mainSplit.setDividerLocation(400);
            mainSplit.setDividerSize(5);
            mainSplit.setBorder(null);

            frame.add(mainSplit, BorderLayout.CENTER);

            BottomBarPanel bottomBar = new BottomBarPanel();
            bottomBar.setOnRefresh(timeline::fireTimelineUpdated);
            frame.add(bottomBar, BorderLayout.SOUTH);

            frame.setLocationRelativeTo(null);
            frame.setVisible(true);
        });
    }
}
