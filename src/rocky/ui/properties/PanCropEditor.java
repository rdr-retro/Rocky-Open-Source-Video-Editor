package rocky.ui.properties;

import javax.swing.*;
import java.awt.*;
import rocky.ui.timeline.TimelineClip;
import rocky.core.media.MediaPool;
import rocky.ui.keyframes.KeyframeTimelinePanel;

/**
 * The main container for the Pan/Crop editor (Sony Vegas style).
 */
public class PanCropEditor extends JPanel {
    private final TimelineClip clip;

    public PanCropEditor(rocky.ui.timeline.TimelinePanel mainTimeline, rocky.ui.timeline.ProjectProperties projectProps,
            TimelineClip clip, MediaPool pool, Runnable onUpdate,
            rocky.core.persistence.HistoryManager historyManager) {
        this.clip = clip;
        setLayout(new BorderLayout());
        setBackground(Color.decode("#0f051d"));

        // --- TOP TOOLBAR ---
        setBackground(Color.decode("#1a0b2e"));
        add(createTopToolbar(), BorderLayout.NORTH);

        // --- CENTER SECTION (Sidebar + Tree + Canvas) ---
        JPanel middleSection = new JPanel(new BorderLayout());
        middleSection.setOpaque(false);

        ToolsSidebar sidebar = new ToolsSidebar();
        middleSection.add(sidebar, BorderLayout.WEST);

        JPanel emptyLeftPanel = new JPanel();
        emptyLeftPanel.setBackground(Color.decode("#1a0b2e"));
        VisualCanvas canvas = new VisualCanvas(clip, pool, historyManager);
        canvas.setContext(mainTimeline, projectProps);

        sidebar.setOnToolSelected(canvas::setCurrentTool);

        canvas.addPropertyChangeListener("transform", e -> {
            if (onUpdate != null)
                onUpdate.run();
        });

        JSplitPane horizontalSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, emptyLeftPanel, canvas);
        horizontalSplit.setDividerLocation(250);
        horizontalSplit.setDividerSize(5);
        horizontalSplit.setBorder(null);

        middleSection.add(horizontalSplit, BorderLayout.CENTER);

        // --- BOTTOM SECTION (Timeline) ---
        KeyframeTimelinePanel timeline = new KeyframeTimelinePanel(clip);

        timeline.setTimelineListener(new rocky.ui.keyframes.KeyframeTimelinePanel.TimelineListener() {
            @Override
            public void onPlayheadChanged(long frame) {
                canvas.setPlayheadFrame(frame);
                // Update clip's working transform to the interpolated one for preview
                clip.setTransform(clip.getInterpolatedTransform(frame));
                if (onUpdate != null)
                    onUpdate.run();
            }
        });

        // Sync with MAIN timeline
        if (mainTimeline != null) {
            mainTimeline.addTimelineListener(new rocky.ui.timeline.TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
                    canvas.setPlayheadFrame(frame);
                    timeline.setPlayheadFrame(frame);
                    repaint();
                }

                @Override
                public void onTimelineUpdated() {}
            });
        }

        JSplitPane verticalSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, middleSection, timeline);
        verticalSplit.setDividerLocation(350);
        verticalSplit.setDividerSize(5);
        verticalSplit.setBorder(null);

        add(verticalSplit, BorderLayout.CENTER);
    }

    private JPanel createTopToolbar() {
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 2));
        toolbar.setBackground(Color.decode("#1a0b2e"));
        toolbar.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.decode("#0f051d")));

        addMockButton(toolbar, "Preset");
        toolbar.add(new JComboBox<>(new String[] { "(Sin nombre)" }));

        return toolbar;
    }

    private void addMockButton(JPanel p, String label) {
        JButton btn = new JButton(label);
        btn.setPreferredSize(new Dimension(60, 20));
        btn.setFont(new Font("Dialog", Font.PLAIN, 10));
        btn.setMargin(new Insets(0, 0, 0, 0));
        p.add(btn);
    }
}
