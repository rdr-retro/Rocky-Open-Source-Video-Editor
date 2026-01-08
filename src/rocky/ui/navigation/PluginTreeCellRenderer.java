package rocky.ui.navigation;

import java.awt.Component;
import java.awt.Color;
import javax.swing.JTree;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeCellRenderer;
import rocky.core.plugins.RockyPlugin;

public class PluginTreeCellRenderer extends DefaultTreeCellRenderer {
    
    // Colors assumed from context or standard theme
    private static final Color BG_PANEL = Color.decode("#1e1e1e"); // darker gray/black
    private static final Color LIST_SELECTION = Color.decode("#7a4f9e"); // Purple
    private static final Color TEXT_PRIMARY = Color.decode("#e0e0e0");
    private static final Color BORDER_COLOR = Color.decode("#333333");

    public PluginTreeCellRenderer() {
        setBackgroundNonSelectionColor(BG_PANEL);
        setBackgroundSelectionColor(LIST_SELECTION);
        setTextNonSelectionColor(TEXT_PRIMARY);
        setTextSelectionColor(Color.WHITE);
        setBorderSelectionColor(BORDER_COLOR);
        setClosedIcon(null);
        setOpenIcon(null);
        setLeafIcon(null);
    }

    @Override
    public Component getTreeCellRendererComponent(JTree tree, Object value, boolean sel, boolean expanded, boolean leaf, int row, boolean hasFocus) {
        super.getTreeCellRendererComponent(tree, value, sel, expanded, leaf, row, hasFocus);
        
        if (value instanceof DefaultMutableTreeNode) {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) value;
            Object userObject = node.getUserObject();
            
            if (userObject instanceof RockyPlugin) {
                setText(((RockyPlugin) userObject).getName());
                // Optional: setToolTipText(((RockyPlugin) userObject).getDescription());
            } else if (userObject instanceof String) {
                setText((String) userObject);
            }
        }
        
        return this;
    }
}
