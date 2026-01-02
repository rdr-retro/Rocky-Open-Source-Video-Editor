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
    private final Color FIELD_BG = Color.decode("#1a0b2e");

    private JComboBox<String> templateCombo, fieldOrderCombo, pixelAspectCombo, fpsCombo, previewResCombo, qualityComboVisor;
    private JComboBox<String> pixelFormatCombo, gammaCombo, qualityCombo, blurTypeCombo, deinterlaceCombo, resampleCombo, acesCombo;
    private JTextField widthField, heightField, renderFolderField;
    private JCheckBox out360Check, adjustSourceCheck, startDefaultCheck, proxyModeCheck, autoDraftCheck;
    private JSlider ramCacheSlider;
    private boolean approved = false;

    public SettingsDialog(Frame parent, ProjectProperties props) {
        super(parent, "Ajustes", true);
        setLayout(new BorderLayout());
        getContentPane().setBackground(BG_COLOR);

        JTabbedPane tabs = new JTabbedPane();
        tabs.setBackground(FIELD_BG);
        tabs.setForeground(TEXT_COLOR);

        tabs.addTab("Vídeo", createVideoTab(props));
        tabs.addTab("Audio", createAudioTab(props));
        tabs.addTab("Visor", createVisorTab(props));

        add(tabs, BorderLayout.CENTER);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 10));
        buttons.setOpaque(false);
        JButton cancel = createStyledButton("Cancelar", false);
        cancel.addActionListener(e -> dispose());
        JButton ok = createStyledButton("Aceptar", true);
        ok.addActionListener(e -> { approved = true; dispose(); });
        buttons.add(cancel);
        buttons.add(ok);
        add(buttons, BorderLayout.SOUTH);

        setPreferredSize(new Dimension(900, 700));
        pack();
        setLocationRelativeTo(parent);
    }

    private JPanel createVideoTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(2, 5, 2, 5);
        gbc.anchor = GridBagConstraints.WEST;

        // --- TOP SECTION ---
        gbc.gridx = 0; gbc.gridy = 0; p.add(createLabel("Plantilla:"), gbc);
        gbc.gridx = 1; gbc.gridwidth = 2;
        String[] templates = {"HD 1080-24p (1920x1080; 23,976 fps)", "HD 720-30p (1280x720; 29,970 fps)", "Custom"};
        templateCombo = createStyledCombo(templates, props.getTemplate());
        p.add(templateCombo, gbc);
        
        gbc.gridwidth = 1; gbc.gridy = 1; gbc.gridx = 0; p.add(createLabel("Anchura:"), gbc);
        gbc.gridx = 1; widthField = createStyledField(String.valueOf(props.getProjectWidth())); p.add(widthField, gbc);
        gbc.gridx = 2; p.add(createLabel("Orden de campos:"), gbc);
        gbc.gridx = 3; fieldOrderCombo = createStyledCombo(new String[]{"Ninguno (escaneo progresivo)", "Campo superior primero"}, props.getFieldOrder()); p.add(fieldOrderCombo, gbc);

        gbc.gridy = 2; gbc.gridx = 0; p.add(createLabel("Altura:"), gbc);
        gbc.gridx = 1; heightField = createStyledField(String.valueOf(props.getProjectHeight())); p.add(heightField, gbc);
        gbc.gridx = 2; p.add(createLabel("Relación de aspecto del píxel:"), gbc);
        gbc.gridx = 3; pixelAspectCombo = createStyledCombo(new String[]{"1,0000 (Cuadrado)", "1,2121 (NTSC Widescreen)"}, props.getPixelAspectRatio()); p.add(pixelAspectCombo, gbc);

        gbc.gridy = 3; gbc.gridx = 2; p.add(createLabel("Inicio de salida:"), gbc);
        gbc.gridx = 3; p.add(createLabel("0 grados (original)"), gbc); // Static for now

        gbc.gridy = 4; gbc.gridx = 0; 
        out360Check = new JCheckBox("Salida 360"); out360Check.setOpaque(false); out360Check.setForeground(TEXT_COLOR); out360Check.setSelected(props.isOut360());
        p.add(out360Check, gbc);
        gbc.gridx = 2; p.add(createLabel("Velocidad de fotogramas:"), gbc);
        gbc.gridx = 3; fpsCombo = createStyledCombo(new String[]{"23,976 (película IVTC)", "24,000", "29,970", "30,000", "60,000"}, String.valueOf(props.getFPS())); p.add(fpsCombo, gbc);

        // --- SEPARATOR (Removing Stereoscopic 3D) ---
        gbc.gridy = 5; gbc.gridx = 0; gbc.gridwidth = 4;
        JSeparator sep = new JSeparator(); sep.setForeground(ACCENT_COLOR); p.add(sep, gbc);

        // --- ADVANCED SECTION ---
        gbc.gridwidth = 2; gbc.gridy = 6; gbc.gridx = 0; p.add(createLabel("Formato de píxel:"), gbc);
        gbc.gridx = 2; pixelFormatCombo = createStyledCombo(new String[]{"8 bits", "32 bits (punto flotante)"}, props.getPixelFormat()); p.add(pixelFormatCombo, gbc);

        gbc.gridy = 7; gbc.gridx = 0; p.add(createLabel("Gamma de composición:"), gbc);
        gbc.gridx = 2; gammaCombo = createStyledCombo(new String[]{"2,222 (Vídeo)", "1,000 (Lineal)"}, props.getGamma()); p.add(gammaCombo, gbc);

        gbc.gridy = 8; gbc.gridx = 0; p.add(createLabel("Versión ACES:"), gbc);
        gbc.gridx = 2; p.add(createLabel("1.0"), gbc);

        gbc.gridy = 9; gbc.gridx = 0; p.add(createLabel("Espacio de color:"), gbc);
        gbc.gridx = 2; 
        acesCombo = createStyledCombo(new String[]{"Predeterminado (sRGB)", "ACES 1.0 (Fílmico)"}, props.isAcesEnabled() ? "ACES 1.0 (Fílmico)" : "Predeterminado (sRGB)");
        p.add(acesCombo, gbc);

        gbc.gridy = 10; gbc.gridx = 0; p.add(createLabel("Transformación de la vista:"), gbc);
        gbc.gridx = 2; p.add(createLabel("Desactivado"), gbc);

        gbc.gridy = 11; gbc.gridx = 0; p.add(createLabel("Calidad de renderización de máx. resolución:"), gbc);
        gbc.gridx = 2; qualityCombo = createStyledCombo(new String[]{"Buena", "Lo mejor", "Borrador"}, props.getRenderingQuality()); p.add(qualityCombo, gbc);

        gbc.gridy = 12; gbc.gridx = 0; p.add(createLabel("Tipo de desenfoque de movimiento:"), gbc);
        gbc.gridx = 2; blurTypeCombo = createStyledCombo(new String[]{"Gausiano", "Piramidal"}, "Gausiano"); p.add(blurTypeCombo, gbc);

        gbc.gridy = 13; gbc.gridx = 0; p.add(createLabel("Método de eliminación de entrelazado:"), gbc);
        gbc.gridx = 2; deinterlaceCombo = createStyledCombo(new String[]{"Ninguno", "Fusionar campos"}, props.getDeinterlaceMethod()); p.add(deinterlaceCombo, gbc);

        gbc.gridy = 14; gbc.gridx = 0; p.add(createLabel("Modo Re-muestreo:"), gbc);
        gbc.gridx = 2; resampleCombo = createStyledCombo(new String[]{"Re-muestreo inteligente", "Forzar re-muestreo"}, props.getResampleMode()); p.add(resampleCombo, gbc);

        gbc.gridy = 15; gbc.gridx = 0; gbc.gridwidth = 4;
        adjustSourceCheck = new JCheckBox("Ajustar medios de origen para que coincidan con la configuración de proyecto o renderización"); adjustSourceCheck.setOpaque(false); adjustSourceCheck.setForeground(TEXT_COLOR);
        p.add(adjustSourceCheck, gbc);

        gbc.gridy = 16; gbc.gridwidth = 1; gbc.gridx = 0; p.add(createLabel("Carpeta de archivos renderizados previamente:"), gbc);
        gbc.gridx = 1; gbc.gridwidth = 2; renderFolderField = createStyledField("/tmp/rocky_renders"); p.add(renderFolderField, gbc);
        gbc.gridx = 3; gbc.gridwidth = 1; p.add(createStyledButton("Examinar...", false), gbc);

        gbc.gridy = 17; gbc.gridx = 0; gbc.gridwidth = 4;
        p.add(createLabel("Espacio disponible en la carpeta seleccionada: 31,4 gigabytes"), gbc);

        gbc.gridy = 18;
        startDefaultCheck = new JCheckBox("Iniciar todos los nuevos proyectos con esta configuración"); startDefaultCheck.setOpaque(false); startDefaultCheck.setForeground(TEXT_COLOR);
        p.add(startDefaultCheck, gbc);

        return p;
    }

    private JPanel createAudioTab(ProjectProperties props) {
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT)); p.setOpaque(false);
        p.add(createLabel("Frecuencia de muestreo (Hz):"));
        p.add(createStyledCombo(new String[]{"44100", "48000", "96000"}, String.valueOf(props.getAudioSampleRate())));
        return p;
    }
    
    private JPanel createVisorTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(10, 5, 10, 5);
        gbc.anchor = GridBagConstraints.WEST;

        gbc.gridx = 0; gbc.gridy = 0;
        p.add(createLabel("Resolución de previsualización:"), gbc);
        
        gbc.gridx = 1;
        String[] resOptions = {
            "320x240 (QVGA)",
            "480x270 (Baja)",
            "640x360 (nHD)",
            "854x480 (SD 480p)",
            "1280x720 (HD 720p)",
            "1920x1080 (Full HD 1080p)",
            "2560x1440 (QHD 1440p)",
            "3840x2160 (4K UHD)"
        };
        previewResCombo = createStyledCombo(resOptions, props.getPreviewRes());
        p.add(previewResCombo, gbc);

        gbc.gridx = 0; gbc.gridy = 1;
        p.add(createLabel("Calidad de previsualización:"), gbc);
        
        gbc.gridx = 1;
        String[] qualityOptions = {"Draft", "Preview", "Good", "Best"};
        qualityComboVisor = createStyledCombo(qualityOptions, props.getPreviewQuality());
        p.add(qualityComboVisor, gbc);

        // --- NEW VEGAS PERFORMANCE OPTIONS ---
        gbc.gridx = 0; gbc.gridy = 2; gbc.gridwidth = 2;
        p.add(new JSeparator(), gbc);
        gbc.gridwidth = 1;

        gbc.gridx = 0; gbc.gridy = 3;
        p.add(createLabel("Límite de RAM para previsualización (MB):"), gbc);
        gbc.gridx = 1;
        ramCacheSlider = new JSlider(128, 4096, props.getRamCacheLimitMB());
        ramCacheSlider.setOpaque(false);
        ramCacheSlider.setMajorTickSpacing(1024);
        ramCacheSlider.setPaintTicks(true);
        p.add(ramCacheSlider, gbc);

        gbc.gridx = 0; gbc.gridy = 4;
        proxyModeCheck = new JCheckBox("Modo Proxy automático (Baja resolución)");
        proxyModeCheck.setOpaque(false); proxyModeCheck.setForeground(TEXT_COLOR);
        proxyModeCheck.setSelected(props.isProxyModeEnabled());
        p.add(proxyModeCheck, gbc);

        gbc.gridx = 1;
        autoDraftCheck = new JCheckBox("Calidad adaptativa (Auto-Draft)");
        autoDraftCheck.setOpaque(false); autoDraftCheck.setForeground(TEXT_COLOR);
        autoDraftCheck.setSelected(props.isAutoDraftQualityEnabled());
        p.add(autoDraftCheck, gbc);

        // Add glue
        gbc.gridy = 5; gbc.weighty = 1.0;
        p.add(Box.createVerticalGlue(), gbc);

        return p;
    }

    private JPanel createPlaceholderTab(String text) {
        JPanel p = new JPanel(); p.setOpaque(false);
        p.add(createLabel(text));
        return p;
    }

    private JLabel createLabel(String text) {
        JLabel l = new JLabel(text); l.setForeground(TEXT_COLOR);
        l.setFont(new Font("SansSerif", Font.PLAIN, 11));
        return l;
    }

    private JTextField createStyledField(String text) {
        JTextField f = new JTextField(text, 10);
        f.setBackground(FIELD_BG); f.setForeground(TEXT_COLOR);
        f.setCaretColor(TEXT_COLOR); f.setBorder(BorderFactory.createLineBorder(ACCENT_COLOR, 1));
        return f;
    }

    private JComboBox<String> createStyledCombo(String[] items, String selected) {
        JComboBox<String> cb = new JComboBox<>(items);
        cb.setSelectedItem(selected);
        cb.setEditable(false);
        cb.setBackground(FIELD_BG); cb.setForeground(TEXT_COLOR);
        return cb;
    }

    private JButton createStyledButton(String text, boolean primary) {
        JButton b = new JButton(text);
        b.setBackground(primary ? ACCENT_COLOR : FIELD_BG); b.setForeground(TEXT_COLOR);
        b.setFocusPainted(false); b.setBorder(BorderFactory.createEmptyBorder(5, 15, 5, 15));
        return b;
    }

    public boolean isApproved() { return approved; }

    public void applyTo(ProjectProperties props) {
        props.setTemplate((String) templateCombo.getSelectedItem());
        props.setProjectRes(widthField.getText() + "x" + heightField.getText());
        props.setPreviewRes((String) previewResCombo.getSelectedItem());
        props.setPreviewQuality((String) qualityComboVisor.getSelectedItem());
        props.setFieldOrder((String) fieldOrderCombo.getSelectedItem());
        props.setPixelAspectRatio((String) pixelAspectCombo.getSelectedItem());
        props.setFPS(Double.parseDouble(((String) fpsCombo.getSelectedItem()).replace(",", ".").split(" ")[0]));
        props.setOut360(out360Check.isSelected());
        props.setPixelFormat((String) pixelFormatCombo.getSelectedItem());
        props.setGamma((String) gammaCombo.getSelectedItem());
        props.setAcesEnabled(((String) acesCombo.getSelectedItem()).contains("ACES"));
        props.setRenderingQuality((String) qualityCombo.getSelectedItem());
        props.setDeinterlaceMethod((String) deinterlaceCombo.getSelectedItem());
        props.setResampleMode((String) resampleCombo.getSelectedItem());
        
        // Vegas model performance fields
        props.setRamCacheLimitMB(ramCacheSlider.getValue());
        props.setProxyModeEnabled(proxyModeCheck.isSelected());
        props.setAutoDraftQualityEnabled(autoDraftCheck.isSelected());
    }
}
