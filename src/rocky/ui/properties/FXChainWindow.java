package rocky.ui.properties;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.*;
import java.util.List;
import rocky.core.plugins.AppliedPlugin;
import rocky.core.plugins.PluginManager;
import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;

/**
 * A dedicated window for managing a chain of effects (Vegas style).
 */
public class FXChainWindow extends JDialog {
    private final List<AppliedPlugin> fxChain;
    private final Runnable onUpdate;
    
    private JList<AppliedPlugin> chainList;
    private DefaultListModel<AppliedPlugin> listModel;
    private JPanel paramsPanel;
    
    private static final Color BG_COLOR = Color.decode("#1e1e1e");
    private static final Color LIST_BG = Color.decode("#252525");
    private static final Color ACCENT = Color.decode("#4a90e2");

    public FXChainWindow(Frame owner, String title, List<AppliedPlugin> fxChain, Runnable onUpdate) {
        super(owner, title, false);
        this.fxChain = fxChain;
        this.onUpdate = onUpdate;
        
        setSize(700, 500);
        setLocationRelativeTo(owner);
        setLayout(new BorderLayout());
        getContentPane().setBackground(BG_COLOR);

        setupUI();
    }

    private void setupUI() {
        // --- TOP TOOLBAR ---
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT));
        toolbar.setBackground(BG_COLOR);
        
        JButton addBtn = createToolbarButton("＋ Añadir Efecto");
        addBtn.addActionListener(e -> showAddEffectDialog());
        
        JButton removeBtn = createToolbarButton("✕ Eliminar");
        removeBtn.addActionListener(e -> removeSelectedEffect());
        
        JButton moveUpBtn = createToolbarButton("↑");
        moveUpBtn.addActionListener(e -> moveEffect(-1));
        
        JButton moveDownBtn = createToolbarButton("↓");
        moveDownBtn.addActionListener(e -> moveEffect(1));
        
        toolbar.add(addBtn);
        toolbar.add(new JSeparator(JSeparator.VERTICAL));
        toolbar.add(removeBtn);
        toolbar.add(moveUpBtn);
        toolbar.add(moveDownBtn);
        
        add(toolbar, BorderLayout.NORTH);

        // --- CENTER SPLIT ---
        listModel = new DefaultListModel<>();
        refreshListModel();
        
        chainList = new JList<>(listModel);
        chainList.setBackground(LIST_BG);
        chainList.setForeground(Color.WHITE);
        chainList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        chainList.setCellRenderer(new FXListCellRenderer());
        chainList.addListSelectionListener(e -> updateParamsPanel());
        
        JScrollPane listScroll = new JScrollPane(chainList);
        listScroll.setPreferredSize(new Dimension(200, 0));
        listScroll.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.BLACK));

        paramsPanel = new JPanel();
        paramsPanel.setLayout(new BoxLayout(paramsPanel, BoxLayout.Y_AXIS));
        paramsPanel.setBackground(BG_COLOR);
        paramsPanel.setBorder(new EmptyBorder(10, 10, 10, 10));
        
        JScrollPane paramsScroll = new JScrollPane(paramsPanel);
        paramsScroll.setBorder(null);
        paramsScroll.getVerticalScrollBar().setUnitIncrement(16);

        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, listScroll, paramsScroll);
        split.setDividerLocation(200);
        split.setBackground(BG_COLOR);
        split.setBorder(null);
        
        add(split, BorderLayout.CENTER);
        
        if (!listModel.isEmpty()) {
            chainList.setSelectedIndex(0);
        }
    }

    private void refreshListModel() {
        listModel.clear();
        synchronized(fxChain) {
            for (AppliedPlugin ap : fxChain) {
                listModel.addElement(ap);
            }
        }
    }

    private void updateParamsPanel() {
        paramsPanel.removeAll();
        AppliedPlugin selected = chainList.getSelectedValue();
        
        if (selected == null) {
            paramsPanel.add(new JLabel("Seleccione un efecto para ver sus parámetros"));
        } else {
            renderEffectParameters(selected);
        }
        
        paramsPanel.revalidate();
        paramsPanel.repaint();
    }

    private void renderEffectParameters(AppliedPlugin applied) {
        JLabel titleLabel = new JLabel(applied.getPluginName().toUpperCase());
        titleLabel.setForeground(ACCENT);
        titleLabel.setFont(new Font("Inter", Font.BOLD, 14));
        titleLabel.setAlignmentX(Component.LEFT_ALIGNMENT);
        paramsPanel.add(titleLabel);
        paramsPanel.add(Box.createVerticalStrut(15));

        RockyEffect effect = PluginManager.getInstance().getEffect(applied.getPluginName());
        if (effect != null) {
            for (PluginParameter param : effect.getParameters()) {
                paramsPanel.add(createParamControl(applied, param));
                paramsPanel.add(Box.createVerticalStrut(10));
            }
        }
    }

    private JPanel createParamControl(AppliedPlugin applied, PluginParameter param) {
        JPanel p = new JPanel(new BorderLayout(10, 0));
        p.setOpaque(false);
        p.setMaximumSize(new Dimension(Integer.MAX_VALUE, 30));
        p.setAlignmentX(Component.LEFT_ALIGNMENT);

        JLabel label = new JLabel(param.getName());
        label.setForeground(Color.LIGHT_GRAY);
        label.setPreferredSize(new Dimension(120, 30));
        p.add(label, BorderLayout.WEST);

        Object currentVal = applied.getParameters().getOrDefault(param.getName(), param.getDefaultValue());

        if (param.getType() == PluginParameter.Type.SLIDER) {
            double min = param.getMin();
            double max = param.getMax();
            int sliderVal = (int) ((((Number) currentVal).doubleValue() - min) / (max - min) * 1000);
            
            JSlider slider = new JSlider(0, 1000, sliderVal);
            slider.setOpaque(false);
            slider.addChangeListener(e -> {
                double newVal = min + (slider.getValue() / 1000.0) * (max - min);
                applied.setParameter(param.getName(), newVal);
                onUpdate.run();
            });
            p.add(slider, BorderLayout.CENTER);
            
            JLabel valLabel = new JLabel(String.format("%.2f", ((Number)currentVal).doubleValue()));
            valLabel.setForeground(Color.WHITE);
            valLabel.setPreferredSize(new Dimension(40, 30));
            p.add(valLabel, BorderLayout.EAST);
            
            slider.addChangeListener(e -> {
                double newVal = min + (slider.getValue() / 1000.0) * (max - min);
                valLabel.setText(String.format("%.2f", newVal));
            });

        } else if (param.getType() == PluginParameter.Type.CHECKBOX) {
            JCheckBox cb = new JCheckBox("", (Boolean) currentVal);
            cb.setOpaque(false);
            cb.addActionListener(e -> {
                applied.setParameter(param.getName(), cb.isSelected());
                onUpdate.run();
            });
            p.add(cb, BorderLayout.CENTER);
        }

        return p;
    }

    private JButton createToolbarButton(String text) {
        JButton btn = new JButton(text);
        btn.setBackground(Color.decode("#333333"));
        btn.setForeground(Color.WHITE);
        btn.setFocusPainted(false);
        btn.setBorder(BorderFactory.createEmptyBorder(5, 10, 5, 10));
        return btn;
    }

    private void showAddEffectDialog() {
        // For simplicity, we'll just show a list of all available effects
        List<RockyEffect> availableEffects = PluginManager.getInstance().getAvailableEffects();
        if (availableEffects.isEmpty()) return;
        
        // Extract names for the dialog
        String[] effectNames = availableEffects.stream()
            .map(RockyEffect::getName)
            .toArray(String[]::new);
        
        String selection = (String) JOptionPane.showInputDialog(this, 
            "Seleccionar efecto para añadir:", "Añadir FX", 
            JOptionPane.PLAIN_MESSAGE, null, 
            effectNames, effectNames[0]);
            
        if (selection != null) {
            AppliedPlugin ap = new AppliedPlugin(selection);
            synchronized(fxChain) {
                fxChain.add(ap);
            }
            refreshListModel();
            chainList.setSelectedValue(ap, true);
            onUpdate.run();
        }
    }

    private void removeSelectedEffect() {
        int idx = chainList.getSelectedIndex();
        if (idx >= 0) {
            synchronized(fxChain) {
                fxChain.remove(idx);
            }
            refreshListModel();
            if (listModel.isEmpty()) {
                updateParamsPanel();
            } else {
                chainList.setSelectedIndex(Math.min(idx, listModel.size() - 1));
            }
            onUpdate.run();
        }
    }

    private void moveEffect(int dir) {
        int idx = chainList.getSelectedIndex();
        int target = idx + dir;
        if (idx >= 0 && target >= 0 && target < listModel.size()) {
            synchronized(fxChain) {
                AppliedPlugin item = fxChain.remove(idx);
                fxChain.add(target, item);
            }
            refreshListModel();
            chainList.setSelectedIndex(target);
            onUpdate.run();
        }
    }

    private class FXListCellRenderer extends DefaultListCellRenderer {
        @Override
        public Component getListCellRendererComponent(JList<?> list, Object value, int index, boolean isSelected, boolean cellHasFocus) {
            AppliedPlugin ap = (AppliedPlugin) value;
            JPanel p = new JPanel(new BorderLayout());
            p.setOpaque(true);
            p.setBackground(isSelected ? ACCENT : LIST_BG);
            
            JCheckBox cb = new JCheckBox("", ap.isEnabled());
            cb.setOpaque(false);
            // Checkbox logic for bypass
            cb.addActionListener(e -> {
                ap.setEnabled(cb.isSelected());
                onUpdate.run();
            });
            
            JLabel label = new JLabel(ap.getPluginName());
            label.setForeground(Color.WHITE);
            label.setBorder(new EmptyBorder(5, 5, 5, 5));
            
            p.add(cb, BorderLayout.WEST);
            p.add(label, BorderLayout.CENTER);
            
            return p;
        }
    }
}
