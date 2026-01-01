package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;

/**
 * A professional settings dialog for Rocky project configuration.
 */
public class SettingsDialog extends JDialog {
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color TEXT_COLOR = Color.decode("#dcd0ff");
    private final Color ACCENT_COLOR = Color.decode("#9d50bb");

    private JComboBox<String> projResCombo;
    private JComboBox<String> previewResCombo;
    private JComboBox<String> fpsCombo;
    private JComboBox<String> sampleRateCombo;
    private JCheckBox lowResCheck;
    private boolean approved = false;

    public SettingsDialog(Frame parent, ProjectProperties props) {
        super(parent, "Ajustes del Proyecto", true);
        setLayout(new BorderLayout());
        getContentPane().setBackground(BG_COLOR);

        JPanel content = new JPanel();
        content.setLayout(new BoxLayout(content, BoxLayout.Y_AXIS));
        content.setOpaque(false);
        content.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));

        String[] resolutions = {
                "3840x2160 (4K Ultra HD)",
                "1920x1080 (Full HD 1080p)",
                "1280x720 (HD 720p)",
                "854x480 (SD 480p)",
                "640x360",
                "480x270"
        };

        projResCombo = createStyledCombo(resolutions, props.getProjectRes());
        previewResCombo = createStyledCombo(resolutions, props.getPreviewRes());
        
        String[] fpsList = {"23.976", "24.0", "25.0", "29.97", "30.0", "50.0", "59.94", "60.0"};
        fpsCombo = createStyledCombo(fpsList, String.valueOf(props.getFPS()));

        String[] sampleRates = {"44100", "48000", "96000"};
        sampleRateCombo = createStyledCombo(sampleRates, String.valueOf(props.getAudioSampleRate()));

        lowResCheck = new JCheckBox("Vista Previa de Baja Resolución (Optimizada)");
        lowResCheck.setSelected(props.isLowResPreview());
        lowResCheck.setOpaque(false);
        lowResCheck.setForeground(TEXT_COLOR);

        addSection(content, "VIDEO");
        addField(content, "Resolución Proyecto:", projResCombo);
        addField(content, "Resolución Previa:", previewResCombo);
        addField(content, "Fotogramas (FPS):", fpsCombo);
        content.add(Box.createVerticalStrut(10));
        content.add(lowResCheck);

        addSection(content, "AUDIO");
        addField(content, "Muestreo (Hz):", sampleRateCombo);

        add(content, BorderLayout.CENTER);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 10));
        buttons.setOpaque(false);
        
        JButton cancel = createStyledButton("Cancelar", false);
        cancel.addActionListener(e -> dispose());
        
        JButton ok = createStyledButton("Aplicar Ajustes", true);
        ok.addActionListener(e -> {
            approved = true;
            dispose();
        });

        buttons.add(cancel);
        buttons.add(ok);
        add(buttons, BorderLayout.SOUTH);

        pack();
        setLocationRelativeTo(parent);
    }

    public boolean isApproved() { return approved; }

    public void applyTo(ProjectProperties props) {
        props.setProjectRes((String) projResCombo.getSelectedItem());
        props.setPreviewRes((String) previewResCombo.getSelectedItem());
        props.setFPS(Double.parseDouble((String) fpsCombo.getSelectedItem()));
        props.setAudioSampleRate(Integer.parseInt((String) sampleRateCombo.getSelectedItem()));
        props.setLowResPreview(lowResCheck.isSelected());
    }

    private void addSection(JPanel p, String title) {
        JLabel l = new JLabel(title);
        l.setForeground(ACCENT_COLOR);
        l.setFont(new Font("SansSerif", Font.BOLD, 12));
        l.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.decode("#1a0b2e")));
        p.add(Box.createVerticalStrut(15));
        p.add(l);
        p.add(Box.createVerticalStrut(10));
    }

    private void addField(JPanel p, String label, JComponent comp) {
        JPanel row = new JPanel(new BorderLayout(10, 0));
        row.setOpaque(false);
        JLabel l = new JLabel(label);
        l.setForeground(TEXT_COLOR);
        l.setPreferredSize(new Dimension(140, 25));
        row.add(l, BorderLayout.WEST);
        row.add(comp, BorderLayout.CENTER);
        p.add(row);
        p.add(Box.createVerticalStrut(5));
    }

    private JComboBox<String> createStyledCombo(String[] items, String selected) {
        JComboBox<String> cb = new JComboBox<>(items);
        cb.setSelectedItem(selected);
        cb.setEditable(true);
        cb.setBackground(Color.decode("#1a0b2e"));
        cb.setForeground(Color.decode("#dcd0ff"));
        return cb;
    }

    private JButton createStyledButton(String text, boolean primary) {
        JButton b = new JButton(text);
        b.setBackground(primary ? ACCENT_COLOR : Color.decode("#1a0b2e"));
        b.setForeground(Color.decode("#dcd0ff"));
        b.setFocusPainted(false);
        b.setBorder(BorderFactory.createEmptyBorder(6, 15, 6, 15));
        return b;
    }
}
