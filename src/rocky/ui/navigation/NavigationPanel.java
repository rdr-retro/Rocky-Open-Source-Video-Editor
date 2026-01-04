package rocky.ui.navigation;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.util.ArrayList;
import java.util.List;
import rocky.core.plugins.PluginManager;

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
    private rocky.ui.timeline.ProjectProperties projectProps;
    private Runnable onUpdateCallback;

    public void setProjectProperties(rocky.ui.timeline.ProjectProperties props, Runnable onUpdate) {
        this.projectProps = props;
        this.onUpdateCallback = onUpdate;
        // Re-initialize content if needed or just let the buttons access the new props
    }

    public NavigationPanel() {
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);

        cardLayout = new CardLayout();
        contentPanel = new JPanel(cardLayout);
        contentPanel.setOpaque(false);

        // Real Templates Panel
        contentPanel.add(createTemplatesPanel(), "Plantillas");
        
        // Plugin Explorer Panels
        contentPanel.add(new PluginExplorerPanel(PluginManager.getInstance().getAvailableEffects()), "Efectos");
        contentPanel.add(new PluginExplorerPanel(PluginManager.getInstance().getAvailableTransitions()), "Transiciones");
        contentPanel.add(new PluginExplorerPanel(PluginManager.getInstance().getAvailableGenerators()), "Generadores");

        add(contentPanel, BorderLayout.CENTER);

        // Bottom Tab Bar
        tabBar = new TabBar();
        add(tabBar, BorderLayout.SOUTH);
    }

    private JPanel createTemplatesPanel() {
        JPanel p = new JPanel();
        p.setOpaque(false);
        // 2 columns, dynamic rows (2x2 grid basically)
        p.setLayout(new GridLayout(0, 2, 15, 15)); 
        p.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));

        p.add(createTemplateButton("<html><center>Estándar<br>4:3</center></html>", "1440x1080 (HD 4:3)", 1440, 1080));
        p.add(createTemplateButton("<html><center>Widescreen<br>16:9</center></html>", "1920x1080 (Full HD 1080p)", 1920, 1080));
        p.add(createTemplateButton("<html><center>Shorts / TikTok<br>9:16</center></html>", "1080x1920 (Vertical HD)", 1080, 1920));
        p.add(createTemplateButton("<html><center>Cinemático<br>21:9</center></html>", "2560x1080 (UltraWide)", 2560, 1080));

        // Add a wrapper to center the grid if needed, or just return p if we want them to fill space
        JPanel wrapper = new JPanel(new BorderLayout());
        wrapper.setOpaque(false);
        wrapper.add(p, BorderLayout.NORTH); // Align to top
        
        // Add Title
        JLabel title = new JLabel("Plantillas de Resolución", SwingConstants.CENTER);
        title.setForeground(Color.WHITE);
        title.setFont(new Font("Dialog", Font.BOLD, 16));
        title.setBorder(BorderFactory.createEmptyBorder(10, 0, 0, 0));
        wrapper.add(title, BorderLayout.NORTH);
        
        // Actually, let's put title above and grid center
        JPanel main = new JPanel(new BorderLayout());
        main.setOpaque(false);
        main.add(title, BorderLayout.NORTH);
        main.add(p, BorderLayout.CENTER);
        
        return main;
    }

    private JButton createTemplateButton(String label, String resString, int w, int h) {
        JButton btn = new JButton(label);
        // Square-ish aspect ratio desired? GridLayout will force them to fill cells.
        // We'll give them a preferred size to hint squareness if space allows
        btn.setPreferredSize(new Dimension(100, 100));
        
        btn.setBackground(new Color(40, 30, 60)); // Darker base
        btn.setForeground(new Color(220, 220, 255));
        btn.setFocusPainted(false);
        btn.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(new Color(100, 90, 140), 1),
            BorderFactory.createEmptyBorder(10, 10, 10, 10)
        ));
        btn.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        btn.setFont(new Font("Dialog", Font.PLAIN, 12));
        
        // Hover effect
        btn.addMouseListener(new MouseAdapter() {
            public void mouseEntered(MouseEvent e) {
                btn.setBackground(new Color(70, 60, 100));
                btn.setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(ACCENT_LILAC, 1),
                    BorderFactory.createEmptyBorder(10, 10, 10, 10)
                ));
            }
            public void mouseExited(MouseEvent e) {
                btn.setBackground(new Color(40, 30, 60));
                btn.setBorder(BorderFactory.createCompoundBorder(
                    BorderFactory.createLineBorder(new Color(100, 90, 140), 1),
                    BorderFactory.createEmptyBorder(10, 10, 10, 10)
                ));
            }
        });
        
        btn.addActionListener(e -> {
            if (projectProps != null) {
                projectProps.setProjectRes(resString);
                projectProps.setDisplayRes(resString);
                projectProps.setPreviewRes((w/2) + "x" + (h/2)); 
                
                if (onUpdateCallback != null) {
                    onUpdateCallback.run();
                }
            }
        });
        
        return btn;
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
        private String[] tabs = {"Plantillas", "Efectos", "Transiciones", "Generadores"};
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
