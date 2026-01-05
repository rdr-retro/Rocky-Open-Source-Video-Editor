

package rocky.ui.toolbar;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * A premium top toolbar replicated to match the provided reference image.
 */
public class RockyTopToolbar extends JPanel {
    private final Color BG_COLOR = Color.decode("#1a0b2e");
    private final Color BORDER_COLOR = Color.decode("#0f051d");
    private final Color ICON_GRAY = Color.decode("#dcd0ff");

    private Runnable onSave;
    private Runnable onOpen;
    private Runnable onSettings;
    private Runnable onRender;

    public void setOnSave(Runnable r) { this.onSave = r; }
    public void setOnOpen(Runnable r) { this.onOpen = r; }
    public void setOnSettings(Runnable r) { this.onSettings = r; }
    public void setOnRender(Runnable r) { this.onRender = r; }

    public RockyTopToolbar() {
        setBackground(BG_COLOR);
        setLayout(new FlowLayout(FlowLayout.LEFT, 12, 6));
        setPreferredSize(new Dimension(0, 38));
        setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, BORDER_COLOR));

        // Group 1: File Operations
        add(createIcon("Cargar", Color.decode("#d4af37"), "LOAD", e -> {
            if (onOpen != null) onOpen.run();
        }));

        add(createIcon("Guardar", Color.decode("#5ba9e1"), "SAVE", e -> {
            if (onSave != null) onSave.run();
        }));
        
        add(createVerticalSeparator());

        // Group: Render
        add(createIcon("Renderizar", Color.decode("#ff4757"), "RENDER", e -> {
            if (onRender != null) onRender.run();
        }));
        
        add(createVerticalSeparator());

        // Group 2: Settings
        add(createIcon("Ajustes", Color.WHITE, "SETTINGS", e -> {
            if (onSettings != null) onSettings.run();
        }));

        add(createVerticalSeparator());

        // Group 3: History
        add(createIcon("Atrás", Color.WHITE, "UNDO", null));
        add(createIcon("Adelante", ICON_GRAY, "REDO", null));
    }

    private JPanel createIcon(String tooltip, Color tint, String type, java.util.function.Consumer<MouseEvent> onClick) {
        JPanel p = new JPanel(new BorderLayout());
        p.setOpaque(false);
        p.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        p.setToolTipText(tooltip);
        
        VectorToolbarIcon icon = new VectorToolbarIcon(type, 18, tint);
        p.add(icon, BorderLayout.CENTER);
        
        if (onClick != null) {
            p.addMouseListener(new ToolbarActionAdapter(onClick));
        }

        if (type.equals("UNDO") || type.equals("REDO")) {
            JPanel historyGroup = new JPanel(new FlowLayout(FlowLayout.LEFT, 2, 0));
            historyGroup.setOpaque(false);
            historyGroup.add(icon);
            JLabel arrow = new JLabel("▾");
            arrow.setForeground(ICON_GRAY);
            arrow.setFont(new Font("SansSerif", Font.PLAIN, 10));
            historyGroup.add(arrow);
            p.removeAll();
            p.add(historyGroup);
        }

        return p;
    }

    private JComponent createVerticalSeparator() {
        JSeparator s = new JSeparator(JSeparator.VERTICAL);
        s.setPreferredSize(new Dimension(2, 20));
        s.setForeground(Color.decode("#0f051d"));
        s.setBackground(Color.decode("#dcd0ff"));
        return s;
    }
}
