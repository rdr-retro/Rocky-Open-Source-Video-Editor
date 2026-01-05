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
import java.util.Collections;

/**
 * PluginExplorerPanel - Sony Vegas Pro Style (FINAL PERFECTO)
 * Effects: Imagen original → Hover: Efecto animado + barra
 * Transitions: Mitad/mitad → Hover: Transición animada + barra  
 * Generators: PREVIEW REAL → Hover: SOLO borde (sin animación)
 */
public class PluginExplorerPanel extends JPanel {
    
    // === VEGAS PRO STYLE COLORS ===
    private final Color BG_DARK = new Color(20, 20, 25);
    private final Color BG_PANEL = new Color(35, 35, 42);
    private final Color GRID_BG = new Color(42, 42, 48);
    private final Color TEXT_PRIMARY = new Color(230, 230, 235);
    private final Color LIST_SELECTION = new Color(65, 65, 85);
    private final Color BORDER_COLOR = new Color(70, 70, 85);
    private final Color TILE_BORDER = new Color(80, 80, 95);
    private final Color HOVER_BORDER = new Color(120, 140, 255);

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
        Collections.sort((List<RockyPlugin>) plugins, (a, b) -> a.getName().compareToIgnoreCase(b.getName()));
        
        setLayout(new BorderLayout());
        setBackground(BG_DARK);

        setupLeftPanel();
        JPanel rightPanel = setupRightPanel();

        JScrollPane leftScroll = createLeftScroll();
        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, leftScroll, rightPanel);
        splitPane.setDividerLocation(220);
        splitPane.setDividerSize(3);
        splitPane.setBorder(null);
        splitPane.setBackground(BG_DARK);
        
        add(splitPane, BorderLayout.CENTER);

        pluginTree.expandRow(0);
        updatePresets(null);
    }

    private void setupLeftPanel() {
        DefaultMutableTreeNode root = new DefaultMutableTreeNode("Root");
        DefaultMutableTreeNode pluginsFolder = new DefaultMutableTreeNode("Plugins");
        root.add(pluginsFolder);

        for (RockyPlugin p : plugins) {
            pluginsFolder.add(new DefaultMutableTreeNode(p));
        }

        pluginTree = new JTree(root);
        pluginTree.setRootVisible(false);
        pluginTree.setShowsRootHandles(true);
        pluginTree.setBackground(BG_PANEL);
        pluginTree.setForeground(TEXT_PRIMARY);
        pluginTree.setRowHeight(20);
        pluginTree.putClientProperty("JTree.lineStyle", "None");
        
        pluginTree.setCellRenderer(new VegasTreeCellRenderer());
        pluginTree.getSelectionModel().setSelectionMode(TreeSelectionModel.SINGLE_TREE_SELECTION);
        
        pluginTree.addTreeSelectionListener(e -> {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) pluginTree.getLastSelectedPathComponent();
            if (node == null) return;
            if (node.isLeaf() && node.getUserObject() instanceof RockyPlugin) {
                updatePresets((RockyPlugin) node.getUserObject());
            } else {
                updatePresets(null);
            }
        });
    }

    private JScrollPane createLeftScroll() {
        JScrollPane scroll = new JScrollPane(pluginTree);
        scroll.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, BORDER_COLOR));
        scroll.getVerticalScrollBar().setUI(new VegasScrollBarUI());
        scroll.setBackground(BG_PANEL);
        scroll.getViewport().setBackground(BG_PANEL);
        return scroll;
    }

    private JPanel setupRightPanel() {
        JPanel rightPanel = new JPanel(new BorderLayout());
        rightPanel.setBackground(GRID_BG);

        JPanel header = new JPanel(new FlowLayout(FlowLayout.LEFT, 12, 8));
        header.setBackground(GRID_BG);
        header.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, BORDER_COLOR));
        
        JLabel lbl = new JLabel("Presets:");
        lbl.setFont(new Font("Segoe UI", Font.BOLD, 12));
        lbl.setForeground(TEXT_PRIMARY);
        header.add(lbl);
        
        presetHeaderLabel = new JLabel("Todos");
        presetHeaderLabel.setFont(new Font("Segoe UI", Font.BOLD, 12));
        presetHeaderLabel.setForeground(new Color(180, 190, 220));
        header.add(presetHeaderLabel);
        
        rightPanel.add(header, BorderLayout.NORTH);

        presetsGrid = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 8));
        presetsGrid.setBackground(GRID_BG);
        presetsGrid.setBorder(new EmptyBorder(12, 12, 12, 12));
        
        JPanel flowWrapper = new JPanel(new BorderLayout());
        flowWrapper.setBackground(GRID_BG);
        flowWrapper.add(presetsGrid, BorderLayout.NORTH);

        JScrollPane gridScroll = new JScrollPane(flowWrapper);
        gridScroll.setBorder(null);
        gridScroll.getVerticalScrollBar().setUI(new VegasScrollBarUI());
        gridScroll.setBackground(GRID_BG);
        gridScroll.getViewport().setBackground(GRID_BG);
        
        rightPanel.add(gridScroll, BorderLayout.CENTER);
        return rightPanel;
    }

    private void updatePresets(RockyPlugin plugin) {
        presetsGrid.removeAll();
        
        if (plugin != null) {
            presetHeaderLabel.setText(plugin.getName());
            addPresetCell(plugin, "Default");
        } else {
            presetHeaderLabel.setText("Todos");
            for (RockyPlugin p : plugins) {
                addPresetCell(p, p.getName());
            }
        }
        
        presetsGrid.revalidate();
        presetsGrid.repaint();
    }

    private void addPresetCell(RockyPlugin plugin, String variantName) {
        presetsGrid.add(new VegasPresetCell(plugin, variantName));
    }

    private class VegasTreeCellRenderer extends DefaultTreeCellRenderer {
        @Override
        public Component getTreeCellRendererComponent(JTree tree, Object value, 
            boolean sel, boolean expanded, boolean leaf, int row, boolean hasFocus) {
            super.getTreeCellRendererComponent(tree, value, sel, expanded, leaf, row, hasFocus);
            
            if (value instanceof DefaultMutableTreeNode) {
                Object userObject = ((DefaultMutableTreeNode) value).getUserObject();
                if (userObject instanceof RockyPlugin) {
                    setText(((RockyPlugin) userObject).getName());
                } else {
                    setText(userObject.toString());
                }
            }
            
            setFont(new Font("Segoe UI", Font.PLAIN, 11));
            setBorder(new EmptyBorder(4, 10, 4, 10));
            
            if (sel) {
                setBackground(LIST_SELECTION);
                setForeground(Color.WHITE);
            } else {
                setBackground(BG_PANEL);
                setForeground(new Color(190, 195, 205));
            }
            setOpaque(true);
            return this;
        }
    }

    private class VegasPresetCell extends JPanel implements PluginTransferHandler.PluginCell {
        private final RockyPlugin plugin;
        private final String variant;
        private final BufferedImage previewStatic;
        private final BufferedImage originalImage;
        private boolean hovered = false;
        private Timer animationTimer;
        private float animationProgress = 0.0f;
        private JPanel thumbPanel;

        public VegasPresetCell(RockyPlugin plugin, String variant) {
            this.plugin = plugin;
            this.variant = variant;
            this.originalImage = flowerBase;
            this.previewStatic = generatePreview(plugin);

            setLayout(new BorderLayout());
            setBackground(BG_PANEL);
            setBorder(BorderFactory.createLineBorder(TILE_BORDER, 1));
            setPreferredSize(new Dimension(120, 95));
            setToolTipText(plugin.getName() + " - " + variant);
            
            setTransferHandler(new PluginTransferHandler());
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));

            thumbPanel = new JPanel() {
                @Override
                protected void paintComponent(Graphics g) {
                    super.paintComponent(g);
                    
                    int thumbWidth = 118;
                    int thumbHeight = 63;
                    
                    if (previewStatic != null) {
                        // Generators SIN animación - solo hover border
                        if (hovered && !(plugin instanceof RockyMediaGenerator)) {
                            BufferedImage frame = generateAnimatedFrame(animationProgress);
                            if (frame != null) {
                                g.drawImage(frame, 0, 0, thumbWidth, thumbHeight, null);
                            }
                        } else {
                            g.drawImage(previewStatic, 0, 0, thumbWidth, thumbHeight, null);
                        }
                    }
                    
                    Graphics2D g2d = (Graphics2D) g;
                    g2d.setColor(new Color(0, 0, 0, 40));
                    g2d.drawRect(1, 1, thumbWidth-1, thumbHeight-1);
                    
                    // Generators SIN barra de progreso
                    if (hovered && !(plugin instanceof RockyMediaGenerator)) {
                        int barHeight = 4;
                        int barY = thumbHeight - barHeight - 2;
                        int barWidth = thumbWidth - 4;
                        int progressWidth = (int)(barWidth * animationProgress);
                        
                        g2d.setColor(new Color(50, 50, 60, 200));
                        g2d.fillRoundRect(2, barY, barWidth, barHeight, 3, 3);
                        
                        if (progressWidth > 0) {
                            GradientPaint gradient = new GradientPaint(
                                2, barY, new Color(100, 120, 255, 220),
                                2 + progressWidth, barY, new Color(150, 200, 255, 220)
                            );
                            g2d.setPaint(gradient);
                            g2d.fillRoundRect(2, barY, progressWidth, barHeight, 3, 3);
                            
                            g2d.setColor(new Color(255, 255, 255, 80));
                            g2d.fillRect(2, barY, progressWidth, 1);
                        }
                    }
                }
            };
            thumbPanel.setPreferredSize(new Dimension(120, 65));
            thumbPanel.setOpaque(false);

            JLabel lbl = new JLabel(variant, SwingConstants.CENTER);
            lbl.setFont(new Font("Segoe UI", Font.PLAIN, 10));
            lbl.setForeground(TEXT_PRIMARY);
            lbl.setBorder(new EmptyBorder(4, 2, 4, 2));

            add(thumbPanel, BorderLayout.CENTER);
            add(lbl, BorderLayout.SOUTH);

            animationTimer = new Timer(30, e -> {
                animationProgress += 0.02f;
                if (animationProgress >= 1.0f) animationProgress = 0.0f;
                thumbPanel.repaint();
            });

            addMouseListener(new MouseAdapter() {
                public void mouseEntered(MouseEvent e) {
                    hovered = true;
                    setBorder(BorderFactory.createLineBorder(HOVER_BORDER, 2));
                    // Generators SIN animación
                    if (!(plugin instanceof RockyMediaGenerator) && 
                        (plugin instanceof RockyEffect || plugin instanceof RockyTransition)) {
                        animationProgress = 0.0f;
                        animationTimer.start();
                    }
                    thumbPanel.repaint();
                }
                public void mouseExited(MouseEvent e) {
                    hovered = false;
                    setBorder(BorderFactory.createLineBorder(TILE_BORDER, 1));
                    animationTimer.stop();
                    thumbPanel.repaint();
                }
                public void mousePressed(MouseEvent e) {
                    JComponent component = (JComponent) e.getSource();
                    TransferHandler handler = component.getTransferHandler();
                    handler.exportAsDrag(component, e, TransferHandler.COPY);
                }
            });
        }

        private BufferedImage generateAnimatedFrame(float progress) {
            if (originalImage == null) return null;
            
            int w = originalImage.getWidth();
            int h = originalImage.getHeight();
            BufferedImage frame = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
            Graphics2D g2 = frame.createGraphics();
            
            if (plugin instanceof RockyMediaGenerator) {
                ((RockyMediaGenerator) plugin).generate(g2, w, h, 0L, new HashMap<>());
            } else {
                g2.drawImage(originalImage, 0, 0, null);
                int wipeX = (int)(w * progress);
                g2.setClip(0, 0, wipeX, h);
                
                if (plugin instanceof RockyEffect) {
                    ((RockyEffect) plugin).apply(originalImage, g2, new HashMap<>());
                } else if (plugin instanceof RockyTransition) {
                    BufferedImage b = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
                    Graphics2D gB = b.createGraphics();
                    gB.setColor(Color.WHITE);
                    gB.fillRect(0, 0, w, h);
                    gB.dispose();
                    g2.setClip(null);
                    ((RockyTransition) plugin).render(g2, w, h, originalImage, b, progress, new HashMap<>());
                }
            }
            
            g2.dispose();
            return frame;
        }

        @Override
        public RockyPlugin getPlugin() {
            return plugin;
        }
    }

    // ✅ FIXED: Generators muestran PREVIEW REAL del generador
    private BufferedImage generatePreview(RockyPlugin plugin) {
        if (flowerBase == null) return null;
        BufferedImage result = new BufferedImage(flowerBase.getWidth(), 
            flowerBase.getHeight(), BufferedImage.TYPE_INT_ARGB);
        Graphics2D g2 = result.createGraphics();
        
        // ✅ GENERADORES: Muestran preview REAL del generador
        if (plugin instanceof RockyMediaGenerator) {
            g2.setColor(new Color(10, 10, 15));
            g2.fillRect(0, 0, result.getWidth(), result.getHeight());
            ((RockyMediaGenerator) plugin).generate(g2, result.getWidth(), result.getHeight(), 0L, new HashMap<>());
        } 
        // EFFECTS/TRANSITIONS: Imagen original
        else {
            g2.setColor(new Color(10, 10, 15));
            g2.fillRect(0, 0, result.getWidth(), result.getHeight());
            g2.drawImage(flowerBase, 0, 0, null);
            
            if (plugin instanceof RockyTransition) {
                int w = result.getWidth(), h = result.getHeight();
                BufferedImage b = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
                Graphics2D gB = b.createGraphics();
                gB.setColor(Color.WHITE);
                gB.setFont(new Font("Segoe UI", Font.BOLD, 48));
                gB.drawString("B", w/2 - 20, h/2 + 15);
                gB.dispose();
                ((RockyTransition) plugin).render(g2, w, h, flowerBase, b, 0.5f, new HashMap<>());
            }
        }
        
        g2.dispose();
        return result;
    }

    private class VegasScrollBarUI extends javax.swing.plaf.basic.BasicScrollBarUI {
        @Override protected void configureScrollBarColors() {
            this.thumbColor = new Color(90, 90, 110);
            this.trackColor = new Color(42, 42, 48);
        }
        @Override protected JButton createDecreaseButton(int orientation) { 
            return createZeroButton(); 
        }
        @Override protected JButton createIncreaseButton(int orientation) { 
            return createZeroButton(); 
        }
        private JButton createZeroButton() {
            JButton b = new JButton();
            b.setPreferredSize(new Dimension(0, 0));
            return b;
        }
    }
}
