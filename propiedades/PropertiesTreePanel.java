package propiedades;

import javax.swing.*;
import javax.swing.tree.*;
import java.awt.*;
import b.timeline.TimelineClip;
import b.timeline.ClipTransform;

/**
 * A tree-based properties editor matching the Sony Vegas style.
 */
public class PropertiesTreePanel extends JPanel {
    private final TimelineClip clip;
    private final JTree tree;
    private final DefaultTreeModel model;

    public PropertiesTreePanel(TimelineClip clip) {
        this.clip = clip;
        setLayout(new BorderLayout());
        setBackground(Color.decode("#1e1e1e"));

        DefaultMutableTreeNode root = new DefaultMutableTreeNode("Propiedades");

        // Posición
        DefaultMutableTreeNode posNode = new DefaultMutableTreeNode("Posición");
        posNode.add(new PropertyNode("Anchura", clip.getTransform().getScaleX() * 1920)); // Mock width
        posNode.add(new PropertyNode("Altura", clip.getTransform().getScaleY() * 1080)); // Mock height
        posNode.add(new PropertyNode("Centro X", clip.getTransform().getX()));
        posNode.add(new PropertyNode("Centro Y", clip.getTransform().getY()));
        root.add(posNode);

        // Rotación
        DefaultMutableTreeNode rotNode = new DefaultMutableTreeNode("Rotación");
        rotNode.add(new PropertyNode("Ángulo", clip.getTransform().getRotation()));
        rotNode.add(new PropertyNode("Centro X", clip.getTransform().getX()));
        rotNode.add(new PropertyNode("Centro Y", clip.getTransform().getY()));
        root.add(rotNode);

        // Others
        root.add(new DefaultMutableTreeNode("Interpolación de fotogramas..."));
        root.add(new DefaultMutableTreeNode("Origen"));
        root.add(new DefaultMutableTreeNode("Área de trabajo"));

        model = new DefaultTreeModel(root);
        tree = new JTree(model);
        tree.setBackground(Color.decode("#1a1a1a"));
        tree.setForeground(Color.WHITE);
        tree.setCellRenderer(new PropertyCellRenderer());

        // Stylize tree
        tree.setShowsRootHandles(true);
        tree.setRootVisible(false);

        JScrollPane scroll = new JScrollPane(tree);
        scroll.setBorder(null);
        add(scroll, BorderLayout.CENTER);

        setPreferredSize(new Dimension(250, 0));
    }

    public void refresh() {
        DefaultMutableTreeNode root = (DefaultMutableTreeNode) model.getRoot();
        root.removeAllChildren();

        // Re-add Posición
        DefaultMutableTreeNode posNode = new DefaultMutableTreeNode("Posición");
        posNode.add(new PropertyNode("Anchura", clip.getTransform().getScaleX() * 1920));
        posNode.add(new PropertyNode("Altura", clip.getTransform().getScaleY() * 1080));
        posNode.add(new PropertyNode("Centro X", clip.getTransform().getX()));
        posNode.add(new PropertyNode("Centro Y", clip.getTransform().getY()));
        root.add(posNode);

        // Re-add Rotación
        DefaultMutableTreeNode rotNode = new DefaultMutableTreeNode("Rotación");
        rotNode.add(new PropertyNode("Ángulo", clip.getTransform().getRotation()));
        rotNode.add(new PropertyNode("Centro X", clip.getTransform().getX()));
        rotNode.add(new PropertyNode("Centro Y", clip.getTransform().getY()));
        root.add(rotNode);

        root.add(new DefaultMutableTreeNode("Interpolación de fotogramas..."));
        root.add(new DefaultMutableTreeNode("Origen"));
        root.add(new DefaultMutableTreeNode("Área de trabajo"));

        model.reload();
    }

    private static class PropertyNode extends DefaultMutableTreeNode {
        private final String name;
        private double value;

        public PropertyNode(String name, double value) {
            this.name = name;
            this.value = value;
        }

        @Override
        public String toString() {
            return name + ": " + String.format("%.1f", value);
        }
    }

    private static class PropertyCellRenderer extends DefaultTreeCellRenderer {
        public PropertyCellRenderer() {
            setOpenIcon(null);
            setClosedIcon(null);
            setLeafIcon(null);
            setBackgroundNonSelectionColor(Color.decode("#1a1a1a"));
            setTextNonSelectionColor(Color.LIGHT_GRAY);
            setTextSelectionColor(Color.WHITE);
            setBorderSelectionColor(Color.decode("#4a90e2"));
        }

        @Override
        public Component getTreeCellRendererComponent(JTree tree, Object value, boolean sel, boolean exp, boolean leaf,
                int row, boolean hasFocus) {
            JLabel label = (JLabel) super.getTreeCellRendererComponent(tree, value, sel, exp, leaf, row, hasFocus);
            label.setForeground(Color.LIGHT_GRAY);
            if (value instanceof DefaultMutableTreeNode) {
                DefaultMutableTreeNode node = (DefaultMutableTreeNode) value;
                if (!node.isLeaf()) {
                    label.setFont(label.getFont().deriveFont(Font.BOLD));
                    label.setText("⊟ " + label.getText()); // Simplified expansion indicator
                } else {
                    label.setText("- " + label.getText());
                }
            }
            return label;
        }
    }
}
