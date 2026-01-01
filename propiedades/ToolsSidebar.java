package propiedades;

import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;
import java.util.List;

/**
 * A vertical toolbar with icons matching the Sony Vegas Pan/Crop style.
 */
public class ToolsSidebar extends JPanel {
    public enum Tool {
        CONFIG, SELECT, EDIT, ZOOM, ASPECT, HORIZ_ONLY, VERT_ONLY, ADD
    }

    private final List<ToolButton> buttons = new ArrayList<>();
    private Tool selectedTool = Tool.SELECT;
    private java.util.function.Consumer<Tool> onToolSelected;

    public ToolsSidebar() {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
        setBackground(Color.decode("#2e2e2e"));
        setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.BLACK));
        setPreferredSize(new Dimension(32, 0));

        // Mock icons based on image
        addTool("⚙", Tool.CONFIG, "Configuración");
        addTool("□", Tool.SELECT, "Seleccionar");
        addTool("↖", Tool.EDIT, "Editar (Pluma)");
        addTool("🔍", Tool.ZOOM, "Zoom");
        addTool("⛓", Tool.ASPECT, "Bloquear Relación Aspecto");
        addTool("↔", Tool.HORIZ_ONLY, "Solo Horizontal");
        addTool("↕", Tool.VERT_ONLY, "Solo Vertical");
        addTool("+", Tool.ADD, "Añadir");

        add(Box.createVerticalGlue());
    }

    public void setOnToolSelected(java.util.function.Consumer<Tool> listener) {
        this.onToolSelected = listener;
    }

    private void addTool(String icon, Tool tool, String tooltip) {
        ToolButton btn = new ToolButton(icon, tool, tooltip);
        buttons.add(btn);
        add(btn);
    }

    private class ToolButton extends JButton {
        private final Tool tool;

        public ToolButton(String icon, Tool tool, String tooltip) {
            super(icon);
            this.tool = tool;
            setToolTipText(tooltip);
            setFocusPainted(false);
            setBorderPainted(false);
            setContentAreaFilled(false);
            setForeground(Color.WHITE);
            setFont(new Font("Dialog", Font.BOLD, 16));
            setMargin(new Insets(2, 2, 2, 2));
            setMaximumSize(new Dimension(32, 32));

            addActionListener(e -> {
                selectedTool = tool;
                if (onToolSelected != null)
                    onToolSelected.accept(tool);
                repaint();
            });
        }

        @Override
        protected void paintComponent(Graphics g) {
            if (selectedTool == tool) {
                g.setColor(Color.decode("#4a90e2"));
                g.fillRect(0, 0, getWidth(), getHeight());
            }
            super.paintComponent(g);
        }
    }
}
