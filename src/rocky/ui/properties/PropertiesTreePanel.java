package rocky.ui.properties;

import javax.swing.*;
import javax.swing.tree.*;
import java.awt.*;
import rocky.core.model.TimelineClip;
import rocky.core.model.ClipTransform;
import rocky.core.plugins.AppliedPlugin;
import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.PluginManager;
import java.util.Map;

/**
 * A tree-based properties editor matching the Sony Vegas style.
 */
public class PropertiesTreePanel extends JPanel {
    private final TimelineClip clip;
    private final JTree tree;
    private final DefaultTreeModel model;
    private Runnable onParameterChanged;

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
        tree.setEditable(true);
        
        // Custom Editor
        tree.setCellEditor(new PropertyCellEditor());

        JScrollPane scroll = new JScrollPane(tree);
        scroll.setBorder(null);
        add(scroll, BorderLayout.CENTER);

        setPreferredSize(new Dimension(250, 0));
    }

    public void setOnParameterChanged(Runnable r) {
        this.onParameterChanged = r;
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

        // Fades & Transitions
        DefaultMutableTreeNode fadeNode = new DefaultMutableTreeNode("Transiciones");
        
        DefaultMutableTreeNode fadeInNode = new DefaultMutableTreeNode("Entrada (Fade In)");
        AppliedPlugin fi = clip.getFadeInTransition();
        fadeInNode.add(new PropertyNode("Plugin", fi != null ? fi.getPluginName() : "(Ninguno)"));
        if (fi != null && fi.getPluginInstance() != null) {
            for (PluginParameter p : fi.getPluginInstance().getParameters()) {
                fadeInNode.add(new PropertyNode(p.getName(), fi.getParameters().getOrDefault(p.getName(), p.getDefaultValue())));
            }
        }
        fadeNode.add(fadeInNode);
        
        DefaultMutableTreeNode fadeOutNode = new DefaultMutableTreeNode("Salida (Fade Out)");
        AppliedPlugin fo = clip.getFadeOutTransition();
        fadeOutNode.add(new PropertyNode("Plugin", fo != null ? fo.getPluginName() : "(Ninguno)"));
        fadeNode.add(fadeOutNode);
        
        root.add(fadeNode);

        // Efectos
        DefaultMutableTreeNode fxRoot = new DefaultMutableTreeNode("Efectos");
        synchronized(clip.getAppliedEffects()) {
            for (AppliedPlugin applied : clip.getAppliedEffects()) {
                DefaultMutableTreeNode fxNode = new DefaultMutableTreeNode(applied.getPluginName());
                // Add parameters as child nodes
                if (applied.getPluginInstance() != null) {
                    for (PluginParameter param : applied.getPluginInstance().getParameters()) {
                        Object val = applied.getParameters().getOrDefault(param.getName(), param.getDefaultValue());
                        fxNode.add(new PropertyNode(param.getName(), val));
                    }
                } else {
                    // Fallback if instance is null but we have saved params
                    for (Map.Entry<String, Object> entry : applied.getParameters().entrySet()) {
                        fxNode.add(new PropertyNode(entry.getKey(), entry.getValue()));
                    }
                }
                fxRoot.add(fxNode);
            }
        }
        root.add(fxRoot);

        model.reload();
    }

    private static class PropertyNode extends DefaultMutableTreeNode {
        private final String name;
        private Object value;

        public PropertyNode(String name, Object value) {
            this.name = name;
            this.value = value;
        }

        @Override
        public String toString() {
            if (value instanceof Double || value instanceof Float || value instanceof Integer) {
                return name + ": " + String.format("%.2f", ((Number)value).doubleValue());
            }
            return name + ": " + value;
        }

        public void setValue(Object value) {
            this.value = value;
        }

        public String getName() { return name; }
        public Object getValue() { return value; }
    }

    private class PropertyCellEditor extends AbstractCellEditor implements TreeCellEditor {
        private final JTextField textField = new JTextField();
        private PropertyNode currentNode;

        public PropertyCellEditor() {
            textField.setBackground(Color.decode("#2a2a2a"));
            textField.setForeground(Color.WHITE);
            textField.setCaretColor(Color.WHITE);
            textField.addActionListener(e -> stopCellEditing());
        }

        @Override
        public Component getTreeCellEditorComponent(JTree tree, Object value, boolean isSelected, boolean expanded, boolean leaf, int row) {
            if (value instanceof PropertyNode) {
                currentNode = (PropertyNode) value;
                textField.setText(String.valueOf(currentNode.getValue()));
                return textField;
            }
            return null;
        }

        @Override
        public Object getCellEditorValue() {
            String text = textField.getText();
            try {
                // Try to parse as double if it was double
                if (currentNode.getValue() instanceof Double) {
                    return Double.parseDouble(text);
                } else if (currentNode.getValue() instanceof Integer) {
                    return Integer.parseInt(text);
                }
            } catch (Exception e) {
                // Ignore parsing errors, keep original
            }
            return text;
        }

        @Override
        public boolean stopCellEditing() {
            Object newValue = getCellEditorValue();
            if (currentNode != null) {
                currentNode.setValue(newValue);
                
                // Update the clip's metadata
                updateClipProperty(currentNode);
                
                if (onParameterChanged != null) onParameterChanged.run();
                if (currentNode.getName().equals("Plugin")) refresh(); // Re-build tree if plugin changes
            }
            return super.stopCellEditing();
        }
    }

    private void updateClipProperty(PropertyNode node) {
        String name = node.getName();
        Object val = node.getValue();
        
        if (name.equals("Centro X")) clip.getTransform().setX(((Number)val).doubleValue());
        else if (name.equals("Centro Y")) clip.getTransform().setY(((Number)val).doubleValue());
        else if (name.equals("Ángulo")) clip.getTransform().setRotation(((Number)val).doubleValue());
        
        DefaultMutableTreeNode parent = (DefaultMutableTreeNode) node.getParent();
        if (parent == null) return;
        
        String parentName = parent.getUserObject().toString();
        
        if (parentName.equals("Entrada (Fade In)")) {
            if (name.equals("Plugin")) {
                if (val.toString().equals("(Ninguno)")) clip.setFadeInTransition(null);
                else {
                    AppliedPlugin ap = new AppliedPlugin(val.toString());
                    ap.setPluginInstance(PluginManager.getInstance().getTransition(val.toString()));
                    clip.setFadeInTransition(ap);
                }
            } else {
                AppliedPlugin ap = clip.getFadeInTransition();
                if (ap != null) ap.setParameter(name, val);
            }
        } else if (parentName.equals("Salida (Fade Out)")) {
             if (name.equals("Plugin")) {
                if (val.toString().equals("(Ninguno)")) clip.setFadeOutTransition(null);
                else {
                    AppliedPlugin ap = new AppliedPlugin(val.toString());
                    ap.setPluginInstance(PluginManager.getInstance().getTransition(val.toString()));
                    clip.setFadeOutTransition(ap);
                }
            }
        } else if (!parentName.equals("Posición") && !parentName.equals("Rotación")) {
            String pluginName = parentName;
            synchronized(clip.getAppliedEffects()) {
                for (AppliedPlugin applied : clip.getAppliedEffects()) {
                    if (applied.getPluginName().equals(pluginName)) {
                        applied.setParameter(name, val);
                        break;
                    }
                }
            }
        }
    }

    /**
     * Updates the values in the tree from the current clip transform
     * without rebuilding the entire structure (to preserve expansion state etc).
     */
    public void updateValues() {
        DefaultMutableTreeNode root = (DefaultMutableTreeNode) model.getRoot();
        
        for (int i = 0; i < root.getChildCount(); i++) {
            DefaultMutableTreeNode category = (DefaultMutableTreeNode) root.getChildAt(i);
            String categoryName = category.getUserObject().toString();
            
            if (categoryName.equals("Posición")) {
                for (int j = 0; j < category.getChildCount(); j++) {
                    PropertyNode node = (PropertyNode) category.getChildAt(j);
                    String name = node.getName();
                    if (name.equals("Anchura")) node.setValue(clip.getTransform().getScaleX() * 1920);
                    else if (name.equals("Altura")) node.setValue(clip.getTransform().getScaleY() * 1080);
                    else if (name.equals("Centro X")) node.setValue(clip.getTransform().getX());
                    else if (name.equals("Centro Y")) node.setValue(clip.getTransform().getY());
                    model.nodeChanged(node);
                }
            }
            else if (categoryName.equals("Rotación")) {
                 for (int j = 0; j < category.getChildCount(); j++) {
                    PropertyNode node = (PropertyNode) category.getChildAt(j);
                    String name = node.getName();
                    if (name.equals("Ángulo")) node.setValue(clip.getTransform().getRotation());
                    else if (name.equals("Centro X")) node.setValue(clip.getTransform().getX());
                    else if (name.equals("Centro Y")) node.setValue(clip.getTransform().getY());
                    model.nodeChanged(node);
                }
            }
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
