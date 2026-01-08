package rocky.ui.viewer;

import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.event.MouseEvent;
import java.util.function.Consumer;

/**
 * A panel that acts as a video visualizer (Part A Right).
 * Replicated to match the provided reference image.
 */
public class VisualizerPanel extends JPanel {
    private final Color ACCENT_LILAC = Color.decode("#dcd0ff");
    private final Color PANEL_BG = Color.decode("#0f051d");
    private final Color CONTROL_BG = Color.decode("#1a0b2e");
    private final Color TEXT_COLOR = Color.decode("#dcd0ff");

    private JLabel projectVal;
    private JLabel previewVal;
    private JLabel displayVal;
    private JLabel frameVal;
    private JLabel qualityVal;

    private JPanel videoArea;
    private JLabel frameDisplayLabel;
    
    // --- BUFFER STATE ---
    private volatile BufferedImage displayFrame; 
    private Consumer<BufferedImage> recycleCallback;
    
    private long bluelineFrame = 0;
    private Runnable onPlay;
    private Runnable onPause;
    private Runnable onStop;
    private boolean lowResPreview = true;
    private rocky.ui.timeline.ProjectProperties projectProps;
    private boolean showHUD = true;
    private double actualFPS = 0;
    private long lastFrameNanos = 0;
    private double[] fpsAlpha = {0.92}; 

    // --- State caching for throttling ---
    private String lastProjectValText = "";
    private String lastPreviewValText = "";
    private String lastDisplayValText = "";
    private String lastFrameValText = "";
    private String lastQualityValText = "";
    private long lastLabelUpdate = 0;

    public VisualizerPanel() {
        setBackground(Color.BLACK);
        setLayout(new BorderLayout());

        // --- Video Area (Center) ---
        videoArea = new JPanel(new BorderLayout()) {
            @Override
            protected void paintComponent(Graphics g) {
                super.paintComponent(g);
                
                if (displayFrame != null) {
                    Graphics2D g2d = (Graphics2D) g;
                    int w = getWidth();
                    int h = getHeight();
                    int imgW = displayFrame.getWidth();
                    int imgH = displayFrame.getHeight();
                    
                    double scale = Math.min((double) w / imgW, (double) h / imgH);
                    int dW = (int) (imgW * scale);
                    int dH = (int) (imgH * scale);
                    int x = (w - dW) / 2;
                    int y = (h - dH) / 2;
                    
                    g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                    g2d.drawImage(displayFrame, x, y, dW, dH, null);

                    if (showHUD) {
                        g2d.setFont(new Font("Monospaced", Font.BOLD, 12));
                        g2d.setColor(new Color(0, 255, 0, 180)); // Pro Green
                        
                        String res = imgW + "x" + imgH;
                        String fpsDisplay = String.format("Preview: %.2f fps", actualFPS);
                        
                        g2d.drawString(res, 20, getHeight() - 40);
                        g2d.drawString(fpsDisplay, 20, getHeight() - 25);
                        
                        if (projectProps != null) {
                            g2d.drawString("Project: " + projectProps.getFPS() + " fps", 20, getHeight() - 55);
                        }
                    }
                }

                if (displayFrame != null) {
                    // Throttle label updates to ~10fps to save EDT layout time
                    long now = System.currentTimeMillis();
                    if (now - lastLabelUpdate > 100) {
                        String dText = displayFrame.getWidth() + "x" + displayFrame.getHeight() + "x32";
                        if (!dText.equals(lastDisplayValText)) {
                            displayVal.setText(dText);
                            lastDisplayValText = dText;
                        }
                        
                        String fText = String.valueOf(bluelineFrame);
                        if (!fText.equals(lastFrameValText)) {
                            frameVal.setText(fText);
                            lastFrameValText = fText;
                        }
                        lastLabelUpdate = now;
                    }
                }
            }
        };
        videoArea.setBackground(new Color(30,30,30));
        videoArea.setDoubleBuffered(true);
        
        frameDisplayLabel = new JLabel("", SwingConstants.CENTER);
        frameDisplayLabel.setForeground(ACCENT_LILAC);
        frameDisplayLabel.setFont(new Font("Monospaced", Font.BOLD, 18));
        videoArea.add(frameDisplayLabel, BorderLayout.CENTER);
        
        add(videoArea, BorderLayout.CENTER);

        // --- South Container ---
        JPanel southContainer = new JPanel();
        southContainer.setLayout(new BoxLayout(southContainer, BoxLayout.Y_AXIS));
        southContainer.setBackground(PANEL_BG);

        // 1. Playback Bar
        JPanel playBar = new JPanel(new FlowLayout(FlowLayout.CENTER, 20, 5));
        playBar.setBackground(CONTROL_BG);
        playBar.setMaximumSize(new Dimension(Integer.MAX_VALUE, 40));
        
        playBar.add(new VectorIcon("PLAY", 12, e -> { if(onPlay != null) onPlay.run(); })); 
        playBar.add(new VectorIcon("PAUSE", 12, e -> { if(onPause != null) onPause.run(); })); 
        playBar.add(new VectorIcon("STOP", 12, e -> { if(onStop != null) onStop.run(); })); 
        playBar.add(new VectorIcon("MENU", 12, null)); 
        
        southContainer.add(playBar);

        // 2. Status Panel (Two Columns)
        JPanel statusPanel = new JPanel(new GridLayout(1, 2, 20, 0));
        statusPanel.setBackground(PANEL_BG);
        statusPanel.setBorder(BorderFactory.createEmptyBorder(10, 15, 10, 15));
        statusPanel.setMaximumSize(new Dimension(Integer.MAX_VALUE, 60));

        // Column Left
        JPanel leftCol = new JPanel();
        leftCol.setLayout(new BoxLayout(leftCol, BoxLayout.Y_AXIS));
        leftCol.setBackground(PANEL_BG);
        
        projectVal = new JLabel("1920x1080x32; 29,970i");
        leftCol.add(createStatusLine("Proyecto:", projectVal, Color.WHITE));
        
        leftCol.add(Box.createVerticalStrut(2));
        
        previewVal = new JLabel("480x270x32; 29,970p");
        leftCol.add(createStatusLine("Vista previa:", previewVal, ACCENT_LILAC));
        statusPanel.add(leftCol);

        // Column Right
        JPanel rightCol = new JPanel();
        rightCol.setLayout(new BoxLayout(rightCol, BoxLayout.Y_AXIS));
        rightCol.setBackground(PANEL_BG);
        
        frameVal = new JLabel("59");
        rightCol.add(createStatusLine("Fotograma:", frameVal, Color.WHITE));
        
        rightCol.add(Box.createVerticalStrut(2));
        
        displayVal = new JLabel("597x336x32");
        rightCol.add(createStatusLine("Visualización:", displayVal, ACCENT_LILAC));
        qualityVal = new JLabel("Preview");
        rightCol.add(createStatusLine("Calidad:", qualityVal, ACCENT_LILAC));
        
        statusPanel.add(rightCol);

        southContainer.add(statusPanel);

        // 3. Tab Bar
        JPanel tabBar = new JPanel();
        tabBar.setLayout(new FlowLayout(FlowLayout.LEFT, 0, 0));
        tabBar.setBackground(Color.decode("#1a0b2e"));
        tabBar.setMaximumSize(new Dimension(Integer.MAX_VALUE, 30));
        tabBar.setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, Color.BLACK));

        tabBar.add(createTab("Vista previa de vídeo", true));
        
        southContainer.add(tabBar);

        add(southContainer, BorderLayout.SOUTH);
    }

    public void setRecycleCallback(Consumer<BufferedImage> callback) {
        this.recycleCallback = callback;
    }

    public void updateFrame(BufferedImage img) {
        if (img == null) return;
        
        // Use a simple atomic swap of the BufferedImage
        BufferedImage old = this.displayFrame;
        this.displayFrame = img;
        
        if (old != null && old != img && recycleCallback != null) {
            recycleCallback.accept(old);
        }
        
        // Calculate ACTUAL playback FPS
        long now = System.nanoTime();
        if (lastFrameNanos > 0) {
            double instantFPS = 1_000_000_000.0 / (now - lastFrameNanos);
            actualFPS = (actualFPS * fpsAlpha[0]) + (instantFPS * (1.0 - fpsAlpha[0]));
        }
        lastFrameNanos = now;

        videoArea.repaint();
    }

    public void setFrameNumber(long frame) {
        this.bluelineFrame = frame;
        videoArea.repaint();
    }

    // --- CUSTOM VECTOR ICON CLASS ---
    private class VectorIcon extends JComponent {
        private String type;
        private int size;
        private boolean hovered = false;

        public VectorIcon(String type, int size, java.util.function.Consumer<MouseEvent> onClick) {
            this.type = type;
            this.size = size;
            setPreferredSize(new Dimension(size + 10, size + 10));
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));

            addMouseListener(new java.awt.event.MouseAdapter() {
                @Override
                public void mouseEntered(MouseEvent e) { hovered = true; repaint(); }
                @Override
                public void mouseExited(MouseEvent e) { hovered = false; repaint(); }
                @Override
                public void mousePressed(MouseEvent e) {
                    if (onClick != null) onClick.accept(e);
                }
            });
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2d = (Graphics2D) g.create();
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            
            int w = getWidth();
            int h = getHeight();
            int iconSize = size;
            int x = (w - iconSize) / 2;
            int y = (h - iconSize) / 2;

            Color baseColor = hovered ? Color.WHITE : TEXT_COLOR;
            g2d.setColor(baseColor);

            switch (type) {
                case "PLAY":
                    // Smooth rounded triangle
                    java.awt.geom.Path2D playPath = new java.awt.geom.Path2D.Double();
                    double r = 4.0; 
                    playPath.moveTo(x + r, y);
                    playPath.lineTo(x + iconSize - r*1.5, y + iconSize/2.0 - r);
                    playPath.quadTo(x + iconSize, y + iconSize/2.0, x + iconSize - r*1.5, y + iconSize/2.0 + r);
                    playPath.lineTo(x + r, y + iconSize);
                    playPath.quadTo(x, y + iconSize, x, y + iconSize - r);
                    playPath.lineTo(x, y + r);
                    playPath.quadTo(x, y, x + r, y);
                    g2d.fill(playPath);
                    break;
                case "PAUSE":
                    int barW = iconSize / 3;
                    g2d.fillRoundRect(x, y, barW, iconSize, 6, 6);
                    g2d.fillRoundRect(x + iconSize - barW, y, barW, iconSize, 6, 6);
                    break;
                case "STOP":
                    // Squircle/Modern rounded square
                    g2d.fillRoundRect(x, y, iconSize, iconSize, 10, 10);
                    break;
                case "MENU":
                    int lineH = 3;
                    int arc = 3;
                    int spacing = (iconSize - (3 * lineH)) / 2;
                    g2d.fillRoundRect(x, y, iconSize, lineH, arc, arc);
                    g2d.fillRoundRect(x, y + lineH + spacing, iconSize, lineH, arc, arc);
                    g2d.fillRoundRect(x, y + 2 * (lineH + spacing), iconSize, lineH, arc, arc);
                    break;
            }
            g2d.dispose();
        }
    }

    public void setOnPlay(Runnable r) { this.onPlay = r; }
    public void setOnPause(Runnable r) { this.onPause = r; }
    public void setOnStop(Runnable r) { this.onStop = r; }

    public void displayFrame(String info) {
        frameDisplayLabel.setText(info);
        videoArea.repaint();
    }

    public void updateProperties(rocky.ui.timeline.ProjectProperties props) {
        this.projectProps = props;
        updateLabelIfChanged(projectVal, props.getProjectRes(), "project");
        updateLabelIfChanged(previewVal, props.getPreviewRes(), "preview");
        updateLabelIfChanged(displayVal, props.getDisplayRes(), "display");
        updateLabelIfChanged(qualityVal, props.getPreviewQuality(), "quality");
        
        this.lowResPreview = props.isLowResPreview();
        repaint();
    }

    private void updateLabelIfChanged(JLabel label, String text, String cacheKey) {
        boolean changed = false;
        switch(cacheKey) {
            case "project": if (!text.equals(lastProjectValText)) { lastProjectValText = text; changed = true; } break;
            case "preview": if (!text.equals(lastPreviewValText)) { lastPreviewValText = text; changed = true; } break;
            case "display": if (!text.equals(lastDisplayValText)) { lastDisplayValText = text; changed = true; } break;
            case "quality": if (!text.equals(lastQualityValText)) { lastQualityValText = text; changed = true; } break;
        }
        if (changed) {
            label.setText(text);
        }
    }

    private JPanel createStatusLine(String labelStr, JLabel val, Color valueColor) {
        JPanel line = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        line.setBackground(PANEL_BG);
        
        JLabel lbl = new JLabel(labelStr);
        lbl.setForeground(TEXT_COLOR);
        lbl.setFont(new Font("Inter", Font.PLAIN, 12));
        
        val.setForeground(valueColor);
        val.setFont(new Font("Inter", Font.PLAIN, 12));
        
        line.add(lbl);
        line.add(Box.createHorizontalStrut(10));
        line.add(val);
        return line;
    }

    private JPanel createTab(String title, boolean selected) {
        JPanel tab = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 5));
        tab.setBackground(selected ? PANEL_BG : Color.decode("#1a0b2e"));
        tab.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.BLACK));
        
        JLabel label = new JLabel(title);
        label.setForeground(selected ? Color.WHITE : Color.GRAY);
        label.setFont(new Font("Inter", Font.PLAIN, 11));
        
        if (selected) {
             tab.add(label);
        } else {
             tab.add(label);
        }
        
        return tab;
    }
}
