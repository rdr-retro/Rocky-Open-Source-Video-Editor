package rocky.ui.toolbar;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * A premium top toolbar replicated to match the provided reference image.
 */
public class TopToolbar extends JPanel {
    private final Color BG_COLOR = Color.decode("#383838");
    private final Color BORDER_COLOR = Color.decode("#202020");
    private final Color ICON_GRAY = Color.decode("#666666");

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
        JPanel openBtn = createIcon("Cargar", Color.decode("#d4af37"), "📂", e -> {
            if (onOpen != null) onOpen.run();
        });
        add(openBtn);

        JPanel saveBtn = createIcon("Guardar", Color.decode("#5ba9e1"), "💾", e -> {
            if (onSave != null) onSave.run();
        });
        add(saveBtn);
        
        add(createVerticalSeparator());

        // Group: Render
        JPanel renderBtn = createIcon("Renderizar", Color.decode("#ff4757"), "🎬", e -> {
            if (onRender != null) onRender.run();
        });
        add(renderBtn);
        
        add(createVerticalSeparator());

        // Group 2: Settings
        add(createIcon("Ajustes", Color.WHITE, "⚙", e -> {
            if (onSettings != null) onSettings.run();
        }));

        add(createVerticalSeparator());

        // Group 3: History
        add(createHistoryIcon("Atrás", Color.WHITE, "↶"));
        add(createHistoryIcon("Adelante", ICON_GRAY, "↷"));
    }

    private JPanel createIcon(String tooltip, Color tint, String symbol, java.util.function.Consumer<MouseEvent> onClick) {
        JPanel p = new JPanel(new BorderLayout());
        p.setOpaque(false);
        p.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        
        JLabel l = new JLabel(symbol);
        l.setForeground(tint);
        l.setFont(new Font("Monospaced", Font.BOLD, 18));
        l.setToolTipText(tooltip);
        
        if (onClick != null) {
            MouseAdapter adapter = new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    System.out.println("Icon clicked: " + tooltip);
                    onClick.accept(e);
                }
            };
            p.addMouseListener(adapter);
            l.addMouseListener(adapter);
        }

        p.add(l, BorderLayout.CENTER);
        return p;
    }

    private JPanel createHistoryIcon(String tooltip, Color tint, String symbol) {
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT, 2, 0));
        p.setOpaque(false);
        p.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        
        JLabel l = new JLabel(symbol);
        l.setForeground(tint);
        l.setFont(new Font("SansSerif", Font.BOLD, 20));
        l.setToolTipText(tooltip);
        
        JLabel arrow = new JLabel("▾");
        arrow.setForeground(ICON_GRAY);
        arrow.setFont(new Font("SansSerif", Font.PLAIN, 10));
        
        p.add(l);
        p.add(arrow);
        return p;
    }

    private JComponent createVerticalSeparator() {
        JSeparator s = new JSeparator(JSeparator.VERTICAL);
        s.setPreferredSize(new Dimension(2, 20));
        s.setForeground(Color.decode("#222222"));
        s.setBackground(Color.decode("#4a4a4a"));
        return s;
    }
}
