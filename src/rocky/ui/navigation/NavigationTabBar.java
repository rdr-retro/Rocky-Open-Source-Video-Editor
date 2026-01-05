package rocky.ui.navigation;

import javax.swing.JPanel;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;

public class NavigationTabBar extends JPanel implements MouseListener {

    // Region: Fields
    private final String[] tabs = {"Plantillas", "Efectos", "Transiciones", "Generadores"};
    private final CardLayout cardLayout;
    private final JPanel contentPanel;
    
    private final Color TAB_BAR_BG;
    private final Color BG_COLOR;
    private final Color ACCENT_LILAC;
    private final Color TEXT_GRAY;
    
    private int selectedIndex = 0;
    // End Region: Fields

    // Region: Constructor
    public NavigationTabBar(CardLayout cardLayout, JPanel contentPanel, Color tabBarBg, Color bgColor, Color accentLilac, Color textGray) {
        this.cardLayout = cardLayout;
        this.contentPanel = contentPanel;
        this.TAB_BAR_BG = tabBarBg;
        this.BG_COLOR = bgColor;
        this.ACCENT_LILAC = accentLilac;
        this.TEXT_GRAY = textGray;
        
        setPreferredSize(new Dimension(0, 32));
        setBackground(TAB_BAR_BG);
        setOpaque(true);
        addMouseListener(this);
    }
    // End Region: Constructor

    // Region: Painting
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
    // End Region: Painting

    // Region: Mouse Listener
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

    @Override
    public void mouseClicked(MouseEvent e) {}
    
    @Override
    public void mouseReleased(MouseEvent e) {}
    
    @Override
    public void mouseEntered(MouseEvent e) {}
    
    @Override
    public void mouseExited(MouseEvent e) {}
    // End Region: Mouse Listener
}
