package rocky.ui.properties;

import javax.swing.*;
import java.awt.*;
import rocky.core.model.TimelineClip;
import rocky.core.logic.TemporalMath;
import rocky.core.media.MediaPool;
import rocky.ui.keyframes.KeyframeTimelinePanel;
import rocky.core.plugins.PluginManager;
import rocky.core.plugins.RockyEffect;
import rocky.core.plugins.AppliedPlugin;

/**
 * The main container for the Pan/Crop editor (Sony Vegas style).
 */
public class PanCropEditor extends JPanel {
    private final TimelineClip clip;
    private final Runnable onUpdate;
    private PropertiesTreePanel treePanel;

    public PanCropEditor(rocky.ui.timeline.TimelinePanel mainTimeline, rocky.ui.timeline.ProjectProperties projectProps,
            TimelineClip clip, MediaPool pool, Runnable onUpdate,
            rocky.core.persistence.HistoryManager historyManager) {
        this.clip = clip;
        this.onUpdate = onUpdate;
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

        this.treePanel = new PropertiesTreePanel(clip);
        treePanel.setOnParameterChanged(() -> {
            if (onUpdate != null)
                onUpdate.run();
        });

        VisualCanvas canvas = new VisualCanvas(clip, pool, historyManager);
        canvas.setContext(mainTimeline, projectProps);

        sidebar.setOnToolSelected(canvas::setCurrentTool);

        canvas.addPropertyChangeListener("transform", e -> {
            treePanel.updateValues();
            if (onUpdate != null)
                onUpdate.run();
        });

        JSplitPane horizontalSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, treePanel, canvas);
        horizontalSplit.setDividerLocation(250);
        horizontalSplit.setDividerSize(5);
        horizontalSplit.setBorder(null);

        middleSection.add(horizontalSplit, BorderLayout.CENTER);

        // --- BOTTOM SECTION (Timeline) ---
        KeyframeTimelinePanel timeline = new KeyframeTimelinePanel(clip);

        timeline.setTimelineListener(new rocky.ui.keyframes.KeyframeTimelinePanel.TimelineListener() {
            @Override
            public void onPlayheadChanged(long clipLocalFrame) {
                // Convert clip-local frame to global timeline frame
                long globalFrame = clip.getStartFrame() + clipLocalFrame;

                // Update main timeline playhead
                if (mainTimeline != null) {
                    mainTimeline.updatePlayheadFromFrame(globalFrame, true);
                }

                canvas.setPlayheadFrame(globalFrame);
                // Update clip's working transform to the interpolated one for preview
                clip.setTransform(TemporalMath.getInterpolatedTransform(clip, clipLocalFrame));
                if (onUpdate != null)
                    onUpdate.run();
            }
        });

        // Sync with MAIN timeline
        if (mainTimeline != null) {
            mainTimeline.addTimelineListener(new rocky.ui.timeline.TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
                    // Convert global timeline frame to clip-local frame
                    long clipLocalFrame = frame - clip.getStartFrame();

                    // Clamp to clip boundaries
                    if (clipLocalFrame < 0)
                        clipLocalFrame = 0;
                    if (clipLocalFrame > clip.getDurationFrames())
                        clipLocalFrame = clip.getDurationFrames();

                    canvas.setPlayheadFrame(frame);
                    timeline.setPlayheadFrame(clipLocalFrame);
                    repaint();
                }

                @Override
                public void onTimelineUpdated() {
                }
            });
        }

        JSplitPane verticalSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, middleSection, timeline);
        verticalSplit.setDividerLocation(520);
        verticalSplit.setDividerSize(5);
        verticalSplit.setBorder(null);

        add(verticalSplit, BorderLayout.CENTER);

        // Force editor to open at START of clip (Frame 0)
        SwingUtilities.invokeLater(() -> {
            timeline.setPlayheadFrame(0);
            canvas.setPlayheadFrame(0);
        });
    }

    private JPanel createTopToolbar() {
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 2));
        toolbar.setBackground(Color.decode("#1a0b2e"));
        toolbar.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.decode("#0f051d")));

        addMockButton(toolbar, "Preset");
        toolbar.add(new JComboBox<>(new String[] { "(Sin nombre)" }));

        JButton fxBtn = new JButton("FX+");
        fxBtn.setPreferredSize(new Dimension(50, 20));
        fxBtn.setFont(new Font("Dialog", Font.BOLD, 10));
        fxBtn.setMargin(new Insets(0, 0, 0, 0));
        fxBtn.setToolTipText("Añadir Efecto");
        fxBtn.addActionListener(e -> {
            JPopupMenu menu = new JPopupMenu();
            for (RockyEffect effect : PluginManager.getInstance().getAvailableEffects()) {
                JMenuItem item = new JMenuItem(effect.getName());
                item.addActionListener(ae -> {
                    AppliedPlugin applied = new AppliedPlugin(effect.getName());
                    applied.setPluginInstance(effect);
                    // Initialize default parameters
                    for (rocky.core.plugins.PluginParameter p : effect.getParameters()) {
                        applied.setParameter(p.getName(), p.getDefaultValue());
                    }
                    clip.addEffect(applied);
                    treePanel.refresh();
                    if (onUpdate != null)
                        onUpdate.run();
                });
                menu.add(item);
            }
            if (menu.getComponentCount() == 0) {
                menu.add(new JMenuItem("No hay plugins cargados"));
            }
            menu.show(fxBtn, 0, fxBtn.getHeight());
        });
        toolbar.add(fxBtn);

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
