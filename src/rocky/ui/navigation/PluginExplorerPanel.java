package rocky.ui.navigation;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import rocky.core.plugins.RockyPlugin;
import java.awt.*;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.io.File;
import rocky.core.plugins.RockyEffect;
import rocky.core.plugins.RockyTransition;
import rocky.core.plugins.RockyMediaGenerator;
import java.util.HashMap;

/**
 * A grid-based panel that displays a list of plugins for a category.
 */
public class PluginExplorerPanel extends JPanel {
    private static BufferedImage flowerBase;
    static {
        try {
            flowerBase = ImageIO.read(new File("src/assets/flower.png"));
        } catch (Exception e) {
            System.err.println("Could not load flower.png");
        }
    }
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color ITEM_BG = Color.decode("#1a0b2e");
    private final Color ACCENT = Color.decode("#dcd0ff");

    public PluginExplorerPanel(List<? extends RockyPlugin> plugins) {
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);
        setOpaque(true);

        JPanel grid = new JPanel(new GridLayout(0, 2, 10, 10));
        grid.setOpaque(false);
        grid.setBorder(new EmptyBorder(15, 15, 15, 15));

        for (RockyPlugin plugin : plugins) {
            grid.add(new PluginCellPanel(plugin));
        }

        JScrollPane scroll = new JScrollPane(grid);
        scroll.setOpaque(false);
        scroll.getViewport().setOpaque(false);
        scroll.setBorder(null);
        scroll.getVerticalScrollBar().setUnitIncrement(16);
        
        add(scroll, BorderLayout.CENTER);
    }

    private class PluginCellPanel extends JPanel implements PluginTransferHandler.PluginCell {
        private final RockyPlugin plugin;
        private final BufferedImage preview;

        public PluginCellPanel(RockyPlugin plugin) {
            this.plugin = plugin;
            this.preview = generatePreview(plugin);
            
            setLayout(new BorderLayout());
            setBackground(ITEM_BG);
            setPreferredSize(new Dimension(120, 150));
            setBorder(BorderFactory.createLineBorder(new Color(255, 255, 255, 10), 1));
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));

            setTransferHandler(new PluginTransferHandler());
            
            // Image area
            JPanel imgArea = new JPanel() {
                @Override
                protected void paintComponent(Graphics g) {
                    super.paintComponent(g);
                    if (preview != null) {
                        int w = getWidth() - 10;
                        int h = getHeight() - 10;
                        g.drawImage(preview, 5, 5, w, h, null);
                    }
                }
            };
            imgArea.setOpaque(false);
            add(imgArea, BorderLayout.CENTER);

            // Name area
            JLabel nameLabel = new JLabel(plugin.getName(), SwingConstants.CENTER);
            nameLabel.setForeground(Color.WHITE);
            nameLabel.setFont(new Font("Inter", Font.PLAIN, 11));
            nameLabel.setBorder(new EmptyBorder(5, 5, 10, 5));
            add(nameLabel, BorderLayout.SOUTH);

            addMouseListener(new MouseAdapter() {
                @Override
                public void mouseEntered(MouseEvent e) {
                    setBackground(new Color(60, 40, 90));
                    setBorder(BorderFactory.createLineBorder(ACCENT, 1));
                }

                @Override
                public void mouseExited(MouseEvent e) {
                    setBackground(ITEM_BG);
                    setBorder(BorderFactory.createLineBorder(new Color(255, 255, 255, 10), 1));
                }
                
                @Override
                public void mousePressed(MouseEvent e) {
                    JComponent c = (JComponent) e.getSource();
                    TransferHandler handler = c.getTransferHandler();
                    handler.exportAsDrag(c, e, TransferHandler.COPY);
                }
            });
        }

        @Override
        public RockyPlugin getPlugin() {
            return plugin;
        }

        private BufferedImage generatePreview(RockyPlugin plugin) {
            if (flowerBase == null) return null;
            BufferedImage result = new BufferedImage(flowerBase.getWidth(), flowerBase.getHeight(), BufferedImage.TYPE_INT_ARGB);
            Graphics2D g2 = result.createGraphics();
            
            if (plugin instanceof RockyEffect) {
                ((RockyEffect) plugin).apply(flowerBase, g2, new HashMap<>());
            } else if (plugin instanceof RockyTransition) {
                // For transition preview, show at 50%
                ((RockyTransition) plugin).render(g2, result.getWidth(), result.getHeight(), flowerBase, flowerBase, 0.5f, new HashMap<>());
            } else if (plugin instanceof RockyMediaGenerator) {
                ((RockyMediaGenerator) plugin).generate(g2, result.getWidth(), result.getHeight(), 0, new HashMap<>());
            } else {
                g2.drawImage(flowerBase, 0, 0, null);
            }
            
            g2.dispose();
            return result;
        }
    }
}
