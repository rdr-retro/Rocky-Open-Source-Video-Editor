package rocky.ui.timeline;

import rocky.core.plugins.AppliedPlugin;
import javax.swing.*;
import java.awt.*;
import java.util.Map;

public class TextEditorDialog extends JDialog {
    private final AppliedPlugin generator;
    private final Runnable onUpdate;
    
    private final JTextArea textArea;
    private final JComboBox<String> fontCombo;
    private final JSpinner sizeSpinner;
    private final JColorChooser colorChooser;

    public TextEditorDialog(Window parent, AppliedPlugin generator, Runnable onUpdate) {
        super(parent, "Editar Texto", ModalityType.APPLICATION_MODAL);
        this.generator = generator;
        this.onUpdate = onUpdate;
        
        setLayout(new BorderLayout());
        setBackground(Color.decode("#1a1025"));
        
        JPanel mainPanel = new JPanel(new BorderLayout(10, 10));
        mainPanel.setBackground(Color.decode("#1a1025"));
        mainPanel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        
        // --- LEFT: Text Area ---
        textArea = new JTextArea(10, 30);
        textArea.setText((String) generator.getParameters().getOrDefault("Texto", ""));
        textArea.setFont(new Font("Arial", Font.PLAIN, 14));
        styleField(textArea);
        
        JScrollPane scroll = new JScrollPane(textArea);
        scroll.setBorder(BorderFactory.createLineBorder(Color.decode("#4a2f63")));
        mainPanel.add(scroll, BorderLayout.CENTER);
        
        // --- RIGHT: Controls ---
        JPanel rightPanel = new JPanel();
        rightPanel.setLayout(new BoxLayout(rightPanel, BoxLayout.Y_AXIS));
        rightPanel.setBackground(Color.decode("#251635"));
        rightPanel.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(Color.decode("#4a2f63")),
            BorderFactory.createEmptyBorder(10, 10, 10, 10)
        ));
        
        // Helper to add vertical spacing
        rightPanel.add(Box.createVerticalStrut(5));

        // Font
        String currentFont = (String) generator.getParameters().getOrDefault("Fuente", "Arial");
        fontCombo = new JComboBox<>(new String[]{"Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma"});
        fontCombo.setSelectedItem(currentFont);
        rightPanel.add(createLabeledPanel("Fuente:", fontCombo));
        
        rightPanel.add(Box.createVerticalStrut(10));

        // Size
        double currentSize = ((Number)generator.getParameters().getOrDefault("Tamaño", 100.0)).doubleValue();
        sizeSpinner = new JSpinner(new SpinnerNumberModel(currentSize, 10.0, 500.0, 1.0));
        styleSpinner(sizeSpinner);
        rightPanel.add(createLabeledPanel("Tamaño:", sizeSpinner));
        
        rightPanel.add(Box.createVerticalStrut(15));

        // Color
        float r = ((Number)generator.getParameters().getOrDefault("Rojo", 1.0)).floatValue();
        float g = ((Number)generator.getParameters().getOrDefault("Verde", 1.0)).floatValue();
        float b = ((Number)generator.getParameters().getOrDefault("Azul", 1.0)).floatValue();
        
        JLabel colorLabel = new JLabel("Color del texto:");
        colorLabel.setForeground(Color.WHITE);
        colorLabel.setAlignmentX(Component.LEFT_ALIGNMENT);
        rightPanel.add(colorLabel);
        
        rightPanel.add(Box.createVerticalStrut(5));

        colorChooser = new JColorChooser(new Color(r, g, b));
        colorChooser.setPreviewPanel(new JPanel()); // Remove default preview to save space
        
        // Hack: Try to style sub-components of ColorChooser recursively (limited success in Swing, but worth a try)
        styleContainer(colorChooser);
        
        rightPanel.add(colorChooser);
        
        mainPanel.add(rightPanel, BorderLayout.EAST);
        add(mainPanel, BorderLayout.CENTER);
        
        // --- BUTTONS ---
        JPanel btnPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        btnPanel.setBackground(Color.decode("#1a1025"));
        btnPanel.setBorder(BorderFactory.createEmptyBorder(0, 15, 15, 15));
        
        JButton cancelBtn = createStyledButton("Cancelar", Color.decode("#4a2f63"));
        cancelBtn.addActionListener(e -> dispose());
        
        JButton okBtn = createStyledButton("Guardar Cambios", Color.decode("#9d50bb"));
        okBtn.addActionListener(e -> saveAndClose());
        
        btnPanel.add(cancelBtn);
        btnPanel.add(okBtn);
        add(btnPanel, BorderLayout.SOUTH);
        
        pack();
        setLocationRelativeTo(parent);
    }
    
    // --- STYLING HELPERS ---
    
    private void styleField(javax.swing.text.JTextComponent c) {
        c.setBackground(Color.decode("#35224e"));
        c.setForeground(Color.WHITE);
        c.setCaretColor(Color.WHITE);
    }

    private void styleSpinner(JSpinner spinner) {
        JComponent editor = spinner.getEditor();
        if (editor instanceof JSpinner.DefaultEditor) {
            styleField(((JSpinner.DefaultEditor)editor).getTextField());
        }
        spinner.setBorder(BorderFactory.createLineBorder(Color.decode("#4a2f63")));
    }

    private void styleContainer(Container c) {
        c.setBackground(Color.decode("#251635"));
        c.setForeground(Color.WHITE);
        for (Component child : c.getComponents()) {
            if (child instanceof Container) {
                styleContainer((Container)child);
            }
        }
    }
    
    private JButton createStyledButton(String text, Color bgColor) {
        JButton btn = new JButton(text);
        btn.setForeground(Color.WHITE);
        btn.setBackground(bgColor);
        btn.setFocusPainted(false);
        btn.setBorderPainted(false);
        btn.setOpaque(true);
        btn.setBorder(BorderFactory.createEmptyBorder(8, 15, 8, 15));
        btn.setFont(new Font("Segoe UI", Font.BOLD, 12));
        return btn;
    }
    
    private JPanel createLabeledPanel(String label, Component comp) {
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT));
        p.setBackground(Color.decode("#251635"));
        p.setAlignmentX(Component.LEFT_ALIGNMENT);
        
        JLabel lbl = new JLabel(label);
        lbl.setForeground(Color.decode("#b0a4c5"));
        lbl.setPreferredSize(new Dimension(60, 20));
        
        p.add(lbl);
        p.add(comp);
        return p;
    }
    
    private void saveAndClose() {
        Map<String, Object> params = generator.getParameters();
        params.put("Texto", textArea.getText());
        params.put("Fuente", fontCombo.getSelectedItem());
        params.put("Tamaño", ((Number)sizeSpinner.getValue()).doubleValue());
        
        Color c = colorChooser.getColor();
        params.put("Rojo", c.getRed() / 255.0);
        params.put("Verde", c.getGreen() / 255.0);
        params.put("Azul", c.getBlue() / 255.0);
        
        onUpdate.run();
        dispose();
    }
}
