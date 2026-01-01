package rocky.ui.navigation;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.util.ArrayList;
import java.util.List;

/**
 * A navigation panel with tabs at the bottom.
 * Filling the gap to the left of the visualizer.
 */
public class NavigationPanel extends JPanel {
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color TAB_BAR_BG = Color.decode("#1a0b2e");
    private final Color ACCENT_LILAC = Color.decode("#dcd0ff");
    private final Color TEXT_GRAY = new Color(150, 140, 180);

    private CardLayout cardLayout;
    private JPanel contentPanel;
    private TabBar tabBar;

    public NavigationPanel() {
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);

        cardLayout = new CardLayout();
        contentPanel = new JPanel(cardLayout);
        contentPanel.setOpaque(false);

        // Add placeholder contents for each tab
        contentPanel.add(createPlaceholder("Medios (Media Pool)"), "Medios");
        contentPanel.add(createPlaceholder("Efectos (Effects)"), "Efectos");
        contentPanel.add(createPlaceholder("Transiciones (Transitions)"), "Transiciones");
        contentPanel.add(createPlaceholder("Generadores (Generators)"), "Generadores");

        add(contentPanel, BorderLayout.CENTER);

        // Bottom Tab Bar
        tabBar = new TabBar();
        add(tabBar, BorderLayout.SOUTH);
    }

    private JPanel createPlaceholder(String text) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        JLabel l = new JLabel(text);
        l.setForeground(TEXT_GRAY);
        l.setFont(new Font("Dialog", Font.BOLD, 14));
        p.add(l);
        return p;
    }

    /**
     * Custom component for the bottom tab bar.
     */
    private class TabBar extends JPanel {
        private String[] tabs = {"Medios", "Efectos", "Transiciones", "Generadores"};
        private int selectedIndex = 0;

        public TabBar() {
            setPreferredSize(new Dimension(0, 32));
            setBackground(TAB_BAR_BG);
            setOpaque(true);

            addMouseListener(new MouseAdapter() {
                @Override
                public void mousePressed(MouseEvent e) {
                    int w = getWidth();
                    int tabWidth = w / tabs.length;
                    int index = e.getX() / tabWidth;
                    if (index >= 0 && index < tabs.length) {
                        selectedIndex = index;
                        cardLayout.show(contentPanel, tabs[selectedIndex]);
                        repaint();
                    }
                }
            });
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2d = (Graphics2D) g;
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int w = getWidth();
            int h = getHeight();
            int tabWidth = w / tabs.length;

            // Optional separator at the top of the bar
            g2d.setColor(BG_COLOR);
            g2d.drawLine(0, 0, w, 0);

            for (int i = 0; i < tabs.length; i++) {
                int tx = i * tabWidth;
                boolean selected = (i == selectedIndex);

                // Highlight background for selected tab
                if (selected) {
                    g2d.setColor(new Color(255, 255, 255, 10)); // Very subtle glow
                    g2d.fillRect(tx, 1, tabWidth, h - 1);
                    
                    // Top accent line (since tabs are at bottom, accent is at the TOP of the bar)
                    g2d.setColor(ACCENT_LILAC);
                    g2d.fillRect(tx, 0, tabWidth, 2);
                }

                // Text
                g2d.setColor(selected ? ACCENT_LILAC : TEXT_GRAY);
                g2d.setFont(new Font("Inter", selected ? Font.BOLD : Font.PLAIN, 12));
                FontMetrics fm = g2d.getFontMetrics();
                int textX = tx + (tabWidth - fm.stringWidth(tabs[i])) / 2;
                int textY = (h + fm.getAscent() - fm.getDescent()) / 2;
                g2d.drawString(tabs[i], textX, textY);

                // Separator
                if (i < tabs.length - 1) {
                    g2d.setColor(new Color(255, 255, 255, 20));
                    g2d.drawLine(tx + tabWidth - 1, 8, tx + tabWidth - 1, h - 8);
                }
            }
        }
    }
}
