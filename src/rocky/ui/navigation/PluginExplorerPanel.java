package rocky.ui.navigation;

import javax.swing.*;
import javax.swing.border.*;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
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
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreeSelectionModel;
import javax.swing.tree.DefaultTreeCellRenderer;
import javax.swing.JTree;
import java.util.HashMap;

/**
 * A professional split-pane explorer for plugins (Sony Vegas Style).
 * Left: Plugin List
 * Right: Visual Presets Grid
 */
public class PluginExplorerPanel extends JPanel {
    
    // --- PURPLE PRO THEME ---
    private final Color BG_DARK = new Color(15, 5, 29);       // #0f051d
    private final Color BG_PANEL = new Color(26, 11, 46);     // #1a0b2e
    private final Color GRID_BG = new Color(35, 15, 60);      // Lighter purple for grid background
    private final Color TEXT_PRIMARY = new Color(220, 220, 255);
    private final Color LIST_SELECTION = new Color(88, 55, 138); // Header/Selection purple
    private final Color BORDER_COLOR = new Color(60, 40, 90);

    private static BufferedImage flowerBase;
    static {
        try {
            flowerBase = ImageIO.read(new File("src/assets/flower.png"));
        } catch (Exception e) {
            System.err.println("Could not load flower.png");
        }
    }

    private JTree pluginTree;
    private JPanel presetsGrid;
    private JLabel presetHeaderLabel;
    private List<? extends RockyPlugin> plugins;
    
    public PluginExplorerPanel(List<? extends RockyPlugin> plugins) {
        this.plugins = plugins;
        setLayout(new BorderLayout());
        setBackground(BG_DARK);

        // 1. LEFT SIDE: Plugin List
        // 1. LEFT SIDE: Plugin Tree
        DefaultMutableTreeNode root = new DefaultMutableTreeNode("Root");
        DefaultMutableTreeNode pluginsFolder = new DefaultMutableTreeNode("Plugins"); // Folder requested by user
        root.add(pluginsFolder);

        for (RockyPlugin p : plugins) {
            pluginsFolder.add(new DefaultMutableTreeNode(p));
        }

        pluginTree = new JTree(root);
        pluginTree.setRootVisible(false); // Hide "Root", show "Plugins" as top-level folder
        pluginTree.setShowsRootHandles(true);
        pluginTree.setBackground(BG_PANEL);
        pluginTree.setForeground(TEXT_PRIMARY);
        
        // Custom Tree Renderer
        pluginTree.setCellRenderer(new PluginTreeCellRenderer());

        pluginTree.getSelectionModel().setSelectionMode(TreeSelectionModel.SINGLE_TREE_SELECTION);
        // Expand "Plugins" folder
        pluginTree.expandRow(0);

        JScrollPane listScroll = new JScrollPane(pluginTree);
        listScroll.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, BORDER_COLOR));
        listScroll.getVerticalScrollBar().setUI(new PurpleScrollBarUI());
        listScroll.setBackground(BG_PANEL);
        listScroll.getViewport().setBackground(BG_PANEL);

        // 2. RIGHT SIDE: Presets Grid
        JPanel rightPanel = new JPanel(new BorderLayout());
        rightPanel.setBackground(GRID_BG);

        // Header "Preset:"
        JPanel header = new JPanel(new FlowLayout(FlowLayout.LEFT, 15, 5));
        header.setBackground(GRID_BG);
        header.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, BORDER_COLOR));
        JLabel lbl = new JLabel("Preset:");
        lbl.setFont(new Font("SansSerif", Font.BOLD, 12));
        lbl.setForeground(TEXT_PRIMARY);
        header.add(lbl);
        
        presetHeaderLabel = new JLabel("");
        presetHeaderLabel.setFont(new Font("SansSerif", Font.ITALIC, 12));
        presetHeaderLabel.setForeground(new Color(180, 180, 220));
        header.add(presetHeaderLabel);
        
        rightPanel.add(header, BorderLayout.NORTH);

        // Grid (Using FlowLayout to prevent stretching single items)
        presetsGrid = new JPanel(new FlowLayout(FlowLayout.LEFT, 15, 15));
        presetsGrid.setBackground(GRID_BG);
        presetsGrid.setBorder(new EmptyBorder(15, 15, 15, 15));
        
        // Wrap grid in a panel that aligns it to top-left to avoid centering if desired, 
        // though FlowLayout.LEFT handles x-axis. FlowLayout usually wraps.
        // To force it to stretch ONLY width but keep height flexible:
        
        // However, standard FlowLayout might not wrap correctly in a ScrollPane 
        // without a custom layout or resize listener. 
        // A better approach for "Grid that packs" is WrapLayout or modified GridBag.
        // BUT for now, since we want 3 columns (Vegas style), let's stick to simple Flow 
        // and fixed size tiles.
        
        // Actually, let's use a wrapper to ensure it starts at top
        JPanel flowWrapper = new JPanel(new BorderLayout());
        flowWrapper.setBackground(GRID_BG);
        flowWrapper.add(presetsGrid, BorderLayout.NORTH); // Pins content to top

        JScrollPane gridScroll = new JScrollPane(flowWrapper);
        gridScroll.setBorder(null);
        gridScroll.getVerticalScrollBar().setUI(new PurpleScrollBarUI());
        gridScroll.setBackground(GRID_BG);
        gridScroll.getViewport().setBackground(GRID_BG);
        
        rightPanel.add(gridScroll, BorderLayout.CENTER);

        // 3. SPLIT PANE
        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, listScroll, rightPanel);
        splitPane.setDividerLocation(200);
        splitPane.setDividerSize(4);
        splitPane.setBorder(null);
        splitPane.setBackground(BG_DARK);
        
        // Customizing Divider (optional, but standard look is okay for now)
        
        add(splitPane, BorderLayout.CENTER);

        // Events
        // Events
        pluginTree.addTreeSelectionListener(e -> {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) pluginTree.getLastSelectedPathComponent();
            if (node == null) return;
            
            if (node.isLeaf() && node.getUserObject() instanceof RockyPlugin) {
                updatePresets((RockyPlugin) node.getUserObject());
            } else {
                updatePresets(null);
            }
        });

        // Show all plugins initially
        updatePresets(null);
    }

    private void updatePresets(RockyPlugin plugin) {
        presetsGrid.removeAll();
        
        if (plugin != null) {
            // Single plugin selected - show just that one
            presetHeaderLabel.setText(plugin.getName());
            addPresetCell(plugin, "Predeterminado");
        } else {
            // Folder selected or nothing - show ALL plugins as squares
            presetHeaderLabel.setText("Plugins");
            for (RockyPlugin p : plugins) {
                addPresetCell(p, p.getName());
            }
        }
        
        presetsGrid.revalidate();
        presetsGrid.repaint();
    }

    private void addPresetCell(RockyPlugin plugin, String variantName) {
        presetsGrid.add(new PluginPresetCell(plugin, variantName));
    }

    // --- RENDERERS & COMPONENTS ---

    private class PluginListRenderer extends DefaultListCellRenderer {
        @Override
        public Component getListCellRendererComponent(JList<?> list, Object value, int index, boolean isSelected, boolean cellHasFocus) {
            JLabel lbl = (JLabel) super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus);
            RockyPlugin p = (RockyPlugin) value;
            lbl.setText(p.getName());
            lbl.setBorder(new EmptyBorder(5, 8, 5, 8));
            lbl.setFont(new Font("SansSerif", Font.PLAIN, 12));
            
            if (isSelected) {
                lbl.setBackground(LIST_SELECTION);
                lbl.setForeground(Color.WHITE);
            } else {
                lbl.setBackground(BG_PANEL);
                lbl.setForeground(new Color(180, 180, 200));
            }
            return lbl;
        }
    }

    /**
     * Represents a single "Preset" visual tile (Thumbnail + Text Below)
     */
    private class PluginPresetCell extends JPanel implements PluginTransferHandler.PluginCell {
        private final RockyPlugin plugin;
        private final String variant;
        private final BufferedImage preview;
        private boolean hovered = false;

        public PluginPresetCell(RockyPlugin plugin, String variant) {
            this.plugin = plugin;
            this.variant = variant;
            this.preview = generatePreview(plugin);

            setLayout(new BorderLayout());
            setBackground(new Color(255, 255, 255, 15)); // Glassy background
            setBorder(BorderFactory.createLineBorder(new Color(100, 80, 140), 1));
            setPreferredSize(new Dimension(140, 120)); // Vegas style 4:3 cards
            
            setTransferHandler(new PluginTransferHandler());
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));

            // Thumbnail Area
            JPanel thumb = new JPanel() {
                @Override
                protected void paintComponent(Graphics g) {
                    super.paintComponent(g);
                    if (preview != null) {
                        g.drawImage(preview, 0, 0, getWidth(), getHeight(), null);
                    }
                    // Inner shadow for depth
                    g.setColor(new Color(0,0,0,50));
                    g.drawRect(0,0,getWidth()-1,getHeight()-1);
                }
            };
            thumb.setPreferredSize(new Dimension(140, 90));
            thumb.setOpaque(false);
            
            // Text Area
            JLabel lbl = new JLabel("<html><center>" + variant + "</center></html>", SwingConstants.CENTER);
            lbl.setFont(new Font("SansSerif", Font.PLAIN, 11));
            lbl.setForeground(TEXT_PRIMARY);
            lbl.setBorder(new EmptyBorder(5, 2, 5, 2));

            add(thumb, BorderLayout.CENTER);
            add(lbl, BorderLayout.SOUTH);

            addMouseListener(new MouseAdapter() {
                public void mouseEntered(MouseEvent e) {
                    hovered = true;
                    setBackground(new Color(100, 80, 160)); // Highlight
                    setBorder(BorderFactory.createLineBorder(new Color(180, 160, 255), 2));
                }
                public void mouseExited(MouseEvent e) {
                    hovered = false;
                    setBackground(new Color(255, 255, 255, 15));
                    setBorder(BorderFactory.createLineBorder(new Color(100, 80, 140), 1));
                }
                public void mousePressed(MouseEvent e) {
                    JComponent c = (JComponent) e.getSource();
                    TransferHandler handler = c.getTransferHandler();
                    handler.exportAsDrag(c, e, TransferHandler.COPY);
                }
            });
        }

        @Override
        public RockyPlugin getPlugin() {
            return plugin; // In real app, we'd wrap plugin + variant into a configuration object
        }
    }

    private BufferedImage generatePreview(RockyPlugin plugin) {
        if (flowerBase == null) return null;
        BufferedImage result = new BufferedImage(flowerBase.getWidth(), flowerBase.getHeight(), BufferedImage.TYPE_INT_ARGB);
        Graphics2D g2 = result.createGraphics();
        
        // Slightly darken bg for drama
        g2.setColor(Color.BLACK);
        g2.fillRect(0,0,result.getWidth(), result.getHeight());
        
        if (plugin instanceof RockyEffect) {
            ((RockyEffect) plugin).apply(flowerBase, g2, new HashMap<>());
        } else if (plugin instanceof RockyTransition) {
             // Split view for transition preview (A | B)
            int w = result.getWidth();
            int h = result.getHeight();
            
            // Draw A (Original)
            g2.drawImage(flowerBase, 0, 0, null);
            
            // Draw B component (White/Text)
            BufferedImage b = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
            Graphics2D gB = b.createGraphics();
            gB.setColor(Color.WHITE);
            gB.setFont(new Font("Arial", Font.BOLD, 64));
            gB.drawString("B", w/2 - 20, h/2 + 20);
            gB.dispose();
            
            ((RockyTransition) plugin).render(g2, w, h, flowerBase, b, 0.5f, new HashMap<>());
        } else if (plugin instanceof RockyMediaGenerator) {
            ((RockyMediaGenerator) plugin).generate(g2, result.getWidth(), result.getHeight(), 0, new HashMap<>());
        } else {
            g2.drawImage(flowerBase, 0, 0, null);
        }
        
        g2.dispose();
        return result;
    }

    // --- PURPLE SCROLLBAR ---
    private class PurpleScrollBarUI extends javax.swing.plaf.basic.BasicScrollBarUI {
        @Override protected void configureScrollBarColors() {
            this.thumbColor = new Color(80, 60, 120);
            this.trackColor = BG_PANEL;
        }
        @Override protected JButton createDecreaseButton(int orientation) { return createZeroButton(); }
        @Override protected JButton createIncreaseButton(int orientation) { return createZeroButton(); }
        private JButton createZeroButton() {
            JButton b = new JButton();
            b.setPreferredSize(new Dimension(0,0));
            return b;
        }
    }
}
