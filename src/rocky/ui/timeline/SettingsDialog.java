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

    // General
    private JComboBox<String> templateCombo;
    private JTextField renderFolderField;
    private JCheckBox startDefaultCheck, adjustSourceCheck;

    // Video
    private JComboBox<String> fieldOrderCombo, pixelAspectCombo, fpsCombo;
    private JComboBox<String> pixelFormatCombo, gammaCombo, qualityCombo, blurTypeCombo, deinterlaceCombo, resampleCombo, acesCombo;
    private JTextField widthField, heightField;
    private JCheckBox out360Check;

    // Audio
    private JComboBox<String> sampleRateCombo, channelsCombo;

    // Performance (Proxy & Visor)
    private JComboBox<String> proxyResCombo, proxyBitrateCombo;
    private JComboBox<String> visorScaleCombo, visorBitrateCombo, visorFPSCombo;

    private boolean approved = false;

    public SettingsDialog(Frame parent, ProjectProperties props) {
        super(parent, "Propiedades del Proyecto", true);
        setLayout(new BorderLayout());
        getContentPane().setBackground(BG_COLOR);

        JTabbedPane tabs = new JTabbedPane();
        // Fix for Windows: Force Basic UI to respect custom background colors
        tabs.setUI(new javax.swing.plaf.basic.BasicTabbedPaneUI());
        tabs.setBackground(FIELD_BG);
        tabs.setForeground(TEXT_COLOR);

        tabs.addTab("General", createGeneralTab(props));
        tabs.addTab("Vídeo", createVideoTab(props));
        tabs.addTab("Audio", createAudioTab(props));
        tabs.addTab("Rendimiento", createPerformanceTab(props));

        add(tabs, BorderLayout.CENTER);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 10));
        buttons.setOpaque(false);
        JButton cancel = createStyledButton("Cancelar", false);
        cancel.addActionListener(e -> dispose());
        JButton ok = createStyledButton("Aceptar", true);
        ok.addActionListener(e -> {
            approved = true;
            dispose();
        });
        buttons.add(cancel);
        buttons.add(ok);
        add(buttons, BorderLayout.SOUTH);

        setPreferredSize(new Dimension(850, 650));
        pack();
        setLocationRelativeTo(parent);
    }

    private JPanel createGeneralTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        // Templates
        gbc.gridx = 0; gbc.gridy = 0;
        p.add(createLabel("Plantilla:"), gbc);
        gbc.gridx = 1; gbc.weightx = 1.0;
        String[] templates = { 
            "HD 1080-60p (1920x1080; 60,000 fps)",
            "HD 1080-30p (1920x1080; 29,970 fps)",
            "HD 1080-24p (1920x1080; 23,976 fps)", 
            "HD 720-60p (1280x720; 60,000 fps)",
            "HD 720-30p (1280x720; 29,970 fps)", 
            "Custom" 
        };
        templateCombo = createStyledCombo(templates, props.getTemplate());
        
        // Template Logic: Update other fields when template changes
        templateCombo.addActionListener(e -> {
            String sel = (String) templateCombo.getSelectedItem();
            if (sel.contains("1080")) { widthField.setText("1920"); heightField.setText("1080"); }
            if (sel.contains("720")) { widthField.setText("1280"); heightField.setText("720"); }
            if (sel.contains("60p")) { fpsCombo.setSelectedItem("60,000"); }
            if (sel.contains("30p")) { fpsCombo.setSelectedItem("29,970"); }
            if (sel.contains("24p")) { fpsCombo.setSelectedItem("23,976 (IVTC)"); }
        });
        
        p.add(templateCombo, gbc);

        // Prerender Folder
        gbc.gridx = 0; gbc.gridy = 1; gbc.weightx = 0;
        p.add(createLabel("Carpeta de Render/Caché:"), gbc);
        gbc.gridx = 1; gbc.weightx = 1.0;
        JPanel folderPanel = new JPanel(new BorderLayout(5, 0));
        folderPanel.setOpaque(false);
        renderFolderField = createStyledField("/tmp/rocky_renders");
        folderPanel.add(renderFolderField, BorderLayout.CENTER);
        folderPanel.add(createStyledButton("...", false), BorderLayout.EAST);
        p.add(folderPanel, gbc);

        // Info
        gbc.gridx = 1; gbc.gridy = 2;
        p.add(createLabel("<html><i>Espacio libre: 31,4 GB</i></html>"), gbc);

        // Checkboxes
        gbc.gridx = 0; gbc.gridy = 3; gbc.gridwidth = 2; gbc.weightx = 1.0;
        adjustSourceCheck = new JCheckBox("Ajustar medios de origen para coincidir con el proyecto");
        adjustSourceCheck.setOpaque(false);
        adjustSourceCheck.setForeground(TEXT_COLOR);
        p.add(adjustSourceCheck, gbc);

        gbc.gridy = 4;
        startDefaultCheck = new JCheckBox("Iniciar nuevos proyectos con esta configuración");
        startDefaultCheck.setOpaque(false);
        startDefaultCheck.setForeground(TEXT_COLOR);
        p.add(startDefaultCheck, gbc);

        // Spacer
        gbc.gridy = 5; gbc.weighty = 1.0;
        p.add(new JPanel() {{ setOpaque(false); }}, gbc);

        return p;
    }

    private JPanel createVideoTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(2, 5, 2, 5); // Tighter vertical spacing
        gbc.anchor = GridBagConstraints.WEST;

        // --- Basic Format ---
        addSectionHeader(p, gbc, 0, "Formato de Vídeo");

        gbc.gridy++;
        gbc.gridx = 0; gbc.gridwidth = 1; p.add(createLabel("Anchura:"), gbc);
        gbc.gridx = 1; widthField = createStyledField(String.valueOf(props.getProjectWidth())); p.add(widthField, gbc);

        gbc.gridx = 2; p.add(createLabel("Altura:"), gbc);
        gbc.gridx = 3; heightField = createStyledField(String.valueOf(props.getProjectHeight())); p.add(heightField, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("FPS:"), gbc);
        gbc.gridx = 1;
        fpsCombo = createStyledCombo(new String[] { "23,976 (IVTC)", "24,000", "29,970", "30,000", "60,000" }, String.valueOf(props.getFPS()));
        p.add(fpsCombo, gbc);

        gbc.gridx = 2; p.add(createLabel("Orden de campos:"), gbc);
        gbc.gridx = 3;
        fieldOrderCombo = createStyledCombo(new String[] { "Ninguno (Progresivo)", "Campo superior primero" }, props.getFieldOrder());
        p.add(fieldOrderCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Relación de aspecto:"), gbc);
        gbc.gridx = 1; gbc.gridwidth = 3;
        pixelAspectCombo = createStyledCombo(new String[] { "1,0000 (Cuadrado)", "1,2121 (NTSC Widescreen)" }, props.getPixelAspectRatio());
        p.add(pixelAspectCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; gbc.gridwidth = 4;
        out360Check = new JCheckBox("Salida 360 (Equirectangular)");
        out360Check.setOpaque(false);
        out360Check.setForeground(TEXT_COLOR);
        out360Check.setSelected(props.isOut360());
        p.add(out360Check, gbc);

        // --- Color Management ---
        addSectionHeader(p, gbc, gbc.gridy + 1, "Color y Procesamiento");
        // Reset gridwidth
        gbc.gridwidth = 1;

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Formato de píxel:"), gbc);
        gbc.gridx = 1;
        pixelFormatCombo = createStyledCombo(new String[] { "8 bits", "32 bits (Flotante)" }, props.getPixelFormat());
        p.add(pixelFormatCombo, gbc);

        gbc.gridx = 2; p.add(createLabel("Gamma:"), gbc);
        gbc.gridx = 3;
        gammaCombo = createStyledCombo(new String[] { "2,222 (Vídeo)", "1,000 (Lineal)" }, props.getGamma());
        p.add(gammaCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Espacio de color (ACES):"), gbc);
        gbc.gridx = 1; gbc.gridwidth = 3;
        acesCombo = createStyledCombo(new String[] { "Predeterminado (sRGB)", "ACES 1.0 (Fílmico)" },
                props.isAcesEnabled() ? "ACES 1.0 (Fílmico)" : "Predeterminado (sRGB)");
        p.add(acesCombo, gbc);
        gbc.gridwidth = 1;

        // --- Rendering ---
        addSectionHeader(p, gbc, gbc.gridy + 1, "Calidad de Renderizado");

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Calidad:"), gbc);
        gbc.gridx = 1;
        qualityCombo = createStyledCombo(new String[] { "Buena", "Lo mejor", "Borrador" }, props.getRenderingQuality());
        p.add(qualityCombo, gbc);

        gbc.gridx = 2; p.add(createLabel("Desenfoque Mov.:"), gbc);
        gbc.gridx = 3;
        blurTypeCombo = createStyledCombo(new String[] { "Gausiano", "Piramidal" }, "Gausiano");
        p.add(blurTypeCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Desentrelazado:"), gbc);
        gbc.gridx = 1;
        deinterlaceCombo = createStyledCombo(new String[] { "Ninguno", "Fusionar campos" }, props.getDeinterlaceMethod());
        p.add(deinterlaceCombo, gbc);

        gbc.gridx = 2; p.add(createLabel("Re-muestreo:"), gbc);
        gbc.gridx = 3;
        resampleCombo = createStyledCombo(new String[] { "Inteligente", "Forzar" }, props.getResampleMode());
        p.add(resampleCombo, gbc);

        // Spacer
        gbc.gridy++; gbc.gridwidth = 4; gbc.weighty = 1.0;
        p.add(new JPanel() {{ setOpaque(false); }}, gbc);

        return p;
    }

    private JPanel createAudioTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        gbc.gridx = 0; gbc.gridy = 0;
        p.add(createLabel("Frecuencia de muestreo (Hz):"), gbc);
        gbc.gridx = 1;
        sampleRateCombo = createStyledCombo(new String[] { "44100", "48000", "96000" }, String.valueOf(props.getAudioSampleRate()));
        p.add(sampleRateCombo, gbc);

        gbc.gridx = 0; gbc.gridy = 1;
        p.add(createLabel("Canales:"), gbc);
        gbc.gridx = 1;
        channelsCombo = createStyledCombo(new String[] { "Estéreo", "Mono", "5.1 Surround" }, props.getAudioChannels() == 1 ? "Mono" : "Estéreo");
        p.add(channelsCombo, gbc);

        // Spacer
        gbc.gridy = 2; gbc.weighty = 1.0;
        p.add(new JPanel() {{ setOpaque(false); }}, gbc);

        return p;
    }

    private JPanel createPerformanceTab(ProjectProperties props) {
        JPanel p = new JPanel(new GridBagLayout());
        p.setOpaque(false);
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        // --- Proxy ---
        addSectionHeader(p, gbc, 0, "Archivos Proxy (Optimización de Edición)");

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Resolución Proxy:"), gbc);
        gbc.gridx = 1;
        proxyResCombo = createStyledCombo(new String[] { "360p", "480p", "720p" }, String.valueOf(props.getProxyHeight()));
        p.add(proxyResCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Calidad/Bitrate:"), gbc);
        gbc.gridx = 1;
        proxyBitrateCombo = createStyledCombo(new String[] { "500k (Rápido)", "1000k (Equilibrado)", "2000k (Calidad)" }, props.getProxyBitrate());
        p.add(proxyBitrateCombo, gbc);

        gbc.gridy++; gbc.gridwidth = 2;
        p.add(createLabel("<html><font color='#808080'><i>Genera copias ligeras de tus vídeos para editar fluido en 4K/8K.</i></font></html>"), gbc);

        // --- Visor ---
        addSectionHeader(p, gbc, gbc.gridy + 1, "Vista Previa en Tiempo Real");

        gbc.gridy++; gbc.gridwidth = 1;
        gbc.gridx = 0; p.add(createLabel("Escala de Resolución:"), gbc);
        gbc.gridx = 1;
        String currentScale = "Media (1/2)";
        if (props.getVisorScale() == 1.0) currentScale = "Completa (Full)";
        else if (props.getVisorScale() == 0.5) currentScale = "Media (1/2)";
        else if (props.getVisorScale() == 0.25) currentScale = "Cuarto (1/4)";
        else if (props.getVisorScale() == 0.125) currentScale = "Octavo (1/8)";
        visorScaleCombo = createStyledCombo(new String[] { "Completa (Full)", "Media (1/2)", "Cuarto (1/4)", "Octavo (1/8)" }, currentScale);
        p.add(visorScaleCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Calidad de Interpolación:"), gbc);
        gbc.gridx = 1;
        visorBitrateCombo = createStyledCombo(new String[] { "Alta (Bilineal)", "Media", "Baja (Nearest Neighbor)" }, props.getVisorBitrate());
        p.add(visorBitrateCombo, gbc);

        gbc.gridy++;
        gbc.gridx = 0; p.add(createLabel("Visor FPS (Fluidez):"), gbc);
        gbc.gridx = 1;
        visorFPSCombo = createStyledCombo(new String[] { "24,000", "30,000", "60,000" }, String.valueOf(props.getVisorFPS()));
        p.add(visorFPSCombo, gbc);

        // Spacer
        gbc.gridy++; gbc.gridwidth = 2; gbc.weighty = 1.0;
        p.add(new JPanel() {{ setOpaque(false); }}, gbc);

        return p;
    }

    private void addSectionHeader(JPanel p, GridBagConstraints gbc, int gridy, String title) {
        gbc.gridx = 0; gbc.gridy = gridy; gbc.gridwidth = 4;
        JLabel l = new JLabel(title);
        l.setForeground(ACCENT_COLOR);
        l.setFont(new Font("SansSerif", Font.BOLD, 12));
        l.setBorder(BorderFactory.createEmptyBorder(10, 0, 5, 0));
        p.add(l, gbc);
        gbc.gridy++;
        p.add(new JSeparator(), gbc);
        // Reset width for next items
        gbc.gridwidth = 1;
    }

    private JLabel createLabel(String text) {
        JLabel l = new JLabel(text);
        l.setForeground(TEXT_COLOR);
        l.setFont(new Font("SansSerif", Font.PLAIN, 11));
        return l;
    }

    private JTextField createStyledField(String text) {
        JTextField f = new JTextField(text, 10);
        f.setBackground(FIELD_BG);
        f.setForeground(TEXT_COLOR);
        f.setCaretColor(TEXT_COLOR);
        f.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(ACCENT_COLOR, 1),
            BorderFactory.createEmptyBorder(2, 4, 2, 4))
        );
        return f;
    }

    private JComboBox<String> createStyledCombo(String[] items, String selected) {
        JComboBox<String> cb = new JComboBox<>(items);
        cb.setSelectedItem(selected);
        cb.setEditable(false);
        // Fix for Windows: Force Basic UI and Custom Renderer to respect dark theme
        cb.setUI(new javax.swing.plaf.basic.BasicComboBoxUI() {
            @Override
            protected JButton createArrowButton() {
                JButton b = new JButton("▼");
                b.setFont(new Font("SansSerif", Font.PLAIN, 8));
                b.setBorder(BorderFactory.createEmptyBorder());
                b.setBackground(ACCENT_COLOR);
                b.setForeground(Color.WHITE);
                b.setFocusPainted(false);
                b.setContentAreaFilled(false);
                b.setOpaque(true);
                return b;
            }
        });
        cb.setBackground(FIELD_BG);
        cb.setForeground(TEXT_COLOR);

        cb.setRenderer(new DefaultListCellRenderer() {
            @Override
            public Component getListCellRendererComponent(JList<?> list, Object value, int index,
                    boolean isSelected, boolean cellHasFocus) {
                super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus);
                setBorder(BorderFactory.createEmptyBorder(2, 4, 2, 4));
                if (isSelected) {
                    setBackground(ACCENT_COLOR);
                    setForeground(Color.WHITE);
                } else {
                    setBackground(FIELD_BG);
                    setForeground(TEXT_COLOR);
                }
                return this;
            }
        });
        return cb;
    }

    private JButton createStyledButton(String text, boolean primary) {
        JButton b = new JButton(text);
        b.setBackground(primary ? ACCENT_COLOR : FIELD_BG);
        b.setForeground(TEXT_COLOR);
        b.setFocusPainted(false);
        b.setBorder(BorderFactory.createEmptyBorder(6, 16, 6, 16));
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        return b;
    }

    public boolean isApproved() {
        return approved;
    }

    public void applyTo(ProjectProperties props) {
        // General
        props.setTemplate((String) templateCombo.getSelectedItem());
        // props.setRenderFolder(renderFolderField.getText()); // Needs support in ProjectProperties if not present

        // Video
        props.setProjectRes(widthField.getText() + "x" + heightField.getText());
        props.setFPS(Double.parseDouble(((String) fpsCombo.getSelectedItem()).split(" ")[0].replace(",", ".")));
        props.setFieldOrder((String) fieldOrderCombo.getSelectedItem());
        props.setPixelAspectRatio((String) pixelAspectCombo.getSelectedItem());
        props.setOut360(out360Check.isSelected());
        props.setPixelFormat((String) pixelFormatCombo.getSelectedItem());
        props.setGamma((String) gammaCombo.getSelectedItem());
        props.setAcesEnabled(((String) acesCombo.getSelectedItem()).contains("ACES"));
        props.setRenderingQuality((String) qualityCombo.getSelectedItem());
        props.setDeinterlaceMethod((String) deinterlaceCombo.getSelectedItem());
        props.setResampleMode(((String) resampleCombo.getSelectedItem()).contains("Inteligente") ? "Re-muestreo inteligente" : "Forzar re-muestreo");

        // Audio
        props.setAudioSampleRate(Integer.parseInt((String) sampleRateCombo.getSelectedItem()));
        String ch = (String) channelsCombo.getSelectedItem();
        props.setAudioChannels(ch.contains("Mono") ? 1 : 2);

        // Performance
        props.setProxyHeight(Integer.parseInt(((String) proxyResCombo.getSelectedItem()).replace("p", "")));
        props.setProxyBitrate(((String) proxyBitrateCombo.getSelectedItem()).split(" ")[0]);
        
        String vScale = (String) visorScaleCombo.getSelectedItem();
        if (vScale.contains("Completa")) props.setVisorScale(1.0);
        else if (vScale.contains("Media")) props.setVisorScale(0.5);
        else if (vScale.contains("Cuarto")) props.setVisorScale(0.25);
        else if (vScale.contains("Octavo")) props.setVisorScale(0.125);
        
        props.setVisorBitrate(((String) visorBitrateCombo.getSelectedItem()).split(" ")[0]);
        
        props.setVisorFPS(Double.parseDouble(((String) visorFPSCombo.getSelectedItem()).split(" ")[0].replace(",", ".")));
    }
}

