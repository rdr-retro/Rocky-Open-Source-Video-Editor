package rocky.ui.toolbar;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * A premium top toolbar replicated to match the provided reference image.
 */
public class TopToolbar extends JPanel {
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

    public TopToolbar() {
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
            MouseAdapter adapter = new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    onClick.accept(e);
                }
            };
            p.addMouseListener(adapter);
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

    // --- CUSTOM VECTOR TOOLBAR ICON CLASS ---
    private static class VectorToolbarIcon extends JComponent {
        private String type;
        private int size;
        private Color tint;

        public VectorToolbarIcon(String type, int size, Color tint) {
            this.type = type;
            this.size = size;
            this.tint = tint;
            setPreferredSize(new Dimension(size + 4, size + 4));
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2d = (Graphics2D) g.create();
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2d.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
            
            int w = getWidth();
            int h = getHeight();
            int iconSize = size;
            int x = (w - iconSize) / 2;
            int y = (h - iconSize) / 2;

            g2d.setColor(tint);
            float strokeW = 1.5f;
            g2d.setStroke(new BasicStroke(strokeW, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));

            switch (type) {
                case "LOAD":
                    java.awt.geom.Path2D folder = new java.awt.geom.Path2D.Double();
                    folder.moveTo(x, y + 3);
                    folder.lineTo(x + 5, y + 3);
                    folder.lineTo(x + 7, y + 5);
                    folder.lineTo(x + iconSize, y + 5);
                    folder.lineTo(x + iconSize, y + iconSize);
                    folder.lineTo(x, y + iconSize);
                    folder.closePath();
                    g2d.draw(folder);
                    break;
                case "SAVE":
                    java.awt.geom.Path2D disk = new java.awt.geom.Path2D.Double();
                    disk.moveTo(x, y);
                    disk.lineTo(x + iconSize - 4, y);
                    disk.lineTo(x + iconSize, y + 4);
                    disk.lineTo(x + iconSize, y + iconSize);
                    disk.lineTo(x, y + iconSize);
                    disk.closePath();
                    g2d.draw(disk);
                    g2d.drawRect(x + 4, y, iconSize - 8, 5);
                    g2d.drawRect(x + 4, y + iconSize - 6, iconSize - 8, 6);
                    break;
                case "RENDER":
                    java.awt.geom.Path2D clap = new java.awt.geom.Path2D.Double();
                    clap.moveTo(x, y + 5);
                    clap.lineTo(x + iconSize, y + 5);
                    clap.lineTo(x + iconSize, y + iconSize);
                    clap.lineTo(x, y + iconSize);
                    clap.closePath();
                    g2d.draw(clap);
                    // Top part angled
                    g2d.rotate(Math.toRadians(-15), x, y + 5);
                    g2d.drawRect(x, y + 1, iconSize, 4);
                    break;
                case "SETTINGS":
                    int cx = x + iconSize / 2;
                    int cy = y + iconSize / 2;
                    int rInner = iconSize / 4;
                    int rOuter = iconSize / 2;
                    for (int i = 0; i < 8; i++) {
                        g2d.rotate(Math.toRadians(45), cx, cy);
                        g2d.drawRect(cx - 1, y, 2, 4);
                    }
                    g2d.drawOval(cx - rInner, cy - rInner, rInner * 2, rInner * 2);
                    break;
                case "UNDO":
                case "REDO":
                    boolean isRedo = type.equals("REDO");
                    if (isRedo) {
                        g2d.drawArc(x, y + 2, iconSize - 4, iconSize - 4, 120, -240);
                        java.awt.geom.Path2D head = new java.awt.geom.Path2D.Double();
                        head.moveTo(x + iconSize - 4, y + 4);
                        head.lineTo(x + iconSize, y - 1);
                        head.lineTo(x + iconSize - 8, y - 1);
                        head.closePath();
                        g2d.fill(head);
                    } else {
                        g2d.drawArc(x + 4, y + 2, iconSize - 4, iconSize - 4, 60, 240);
                        java.awt.geom.Path2D head = new java.awt.geom.Path2D.Double();
                        head.moveTo(x + 4, y + 4);
                        head.lineTo(x, y - 1);
                        head.lineTo(x + 8, y - 1);
                        head.closePath();
                        g2d.fill(head);
                    }
                    break;
            }
            g2d.dispose();
        }
    }

    private JComponent createVerticalSeparator() {
        JSeparator s = new JSeparator(JSeparator.VERTICAL);
        s.setPreferredSize(new Dimension(2, 20));
        s.setForeground(Color.decode("#0f051d"));
        s.setBackground(Color.decode("#dcd0ff"));
        return s;
    }
}
