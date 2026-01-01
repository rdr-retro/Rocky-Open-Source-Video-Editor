package propiedades;

import javax.swing.*;
import java.awt.*;
import b.timeline.TimelineClip;
import egine.media.MediaPool;
import propiedades.timelinekeyframes.TimelinePanel;

/**
 * The main container for the Pan/Crop editor (Sony Vegas style).
 */
public class PanCropEditor extends JPanel {
    private final TimelineClip clip;

    public PanCropEditor(TimelineClip clip, MediaPool pool, Runnable onUpdate) {
        this.clip = clip;
        setLayout(new BorderLayout());
        setBackground(Color.decode("#1e1e1e"));

        // --- TOP TOOLBAR ---
        setBackground(Color.decode("#252525"));
        add(createTopToolbar(), BorderLayout.NORTH);

        // --- CENTER SECTION (Sidebar + Tree + Canvas) ---
        JPanel middleSection = new JPanel(new BorderLayout());
        middleSection.setOpaque(false);

        ToolsSidebar sidebar = new ToolsSidebar();
        middleSection.add(sidebar, BorderLayout.WEST);

        PropertiesTreePanel treePanel = new PropertiesTreePanel(clip);
        VisualCanvas canvas = new VisualCanvas(clip, pool);

        sidebar.setOnToolSelected(canvas::setCurrentTool);

        canvas.addPropertyChangeListener("transform", e -> {
            treePanel.refresh();
            if (onUpdate != null)
                onUpdate.run();
        });

        JSplitPane horizontalSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, treePanel, canvas);
        horizontalSplit.setDividerLocation(250);
        horizontalSplit.setDividerSize(5);
        horizontalSplit.setBorder(null);
        middleSection.add(horizontalSplit, BorderLayout.CENTER);

        // --- BOTTOM SECTION (Timeline) ---
        TimelinePanel timeline = new TimelinePanel(clip);

        JSplitPane verticalSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, middleSection, timeline);
        verticalSplit.setDividerLocation(400);
        verticalSplit.setDividerSize(8);
        verticalSplit.setBorder(null);

        add(verticalSplit, BorderLayout.CENTER);
    }

    private JPanel createTopToolbar() {
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 2));
        toolbar.setBackground(Color.decode("#333333"));
        toolbar.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.BLACK));

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
