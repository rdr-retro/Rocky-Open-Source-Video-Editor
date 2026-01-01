package b.timeline;

import a.visor.VisualizerPanel;
import a.mastersound.MasterSoundPanel;
import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;

public class TimelineApp {
    public static void main(String[] args) {
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
            SidebarPanel sidebar = new SidebarPanel();
            TimelinePanel timeline = new TimelinePanel();
            TimelineRuler ruler = new TimelineRuler(timeline);

            sidebar.setOnAddTrack(() -> {
                timeline.setTrackHeights(sidebar.getTrackHeights());
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

            timeline.setTimelineListener(new TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
                    sidebar.setTimecode(timecode);
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

            // --- MAIN LAYOUT: JSplitPane ---
            JSplitPane mainSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, topPanel, centerContainer);
            mainSplit.setDividerLocation(400);
            mainSplit.setDividerSize(5);
            mainSplit.setBorder(null);

            frame.add(mainSplit, BorderLayout.CENTER);

            BottomBarPanel bottomBar = new BottomBarPanel();
            frame.add(bottomBar, BorderLayout.SOUTH);

            frame.setLocationRelativeTo(null);
            frame.setVisible(true);
        });
    }
}
