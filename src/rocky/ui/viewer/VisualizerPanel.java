package rocky.ui.viewer;

import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.image.VolatileImage;
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
    
    // --- SIMPLE BUFFER STATE ---
    private volatile BufferedImage displayFrame; 
    
    // Audit / FPS Logic
    private long lastPaintTime = 0;
    private int paintCount = 0;
    private long lastFpsLog = 0;
    
    // Member Variables
    private Consumer<BufferedImage> recycleCallback;
    private long bluelineFrame = 0;
    private Runnable onPlay;
    private Runnable onPause;
    private Runnable onStop;
    private boolean lowResPreview = true;

    public VisualizerPanel() {
        setBackground(Color.BLACK);
        setLayout(new BorderLayout());

        // --- Video Area (Center) ---
        videoArea = new JPanel(new BorderLayout()) {
            @Override
            protected void paintComponent(Graphics g) {
                super.paintComponent(g);
                Graphics2D g2d = (Graphics2D) g;

                // DIAGNOSTIC AUDIT: FPS Counter
                paintCount++;
                long now = System.currentTimeMillis();
                if (now - lastFpsLog > 1000) {
                    System.out.println("[Visualizer] Display FPS: " + paintCount);
                    paintCount = 0;
                    lastFpsLog = now;
                }

                if (displayFrame != null) {
                    // DIRECT DRAW with Aspect Ratio Preservation
                    int panelW = getWidth();
                    int panelH = getHeight();
                    int imgW = displayFrame.getWidth();
                    int imgH = displayFrame.getHeight();

                    if (imgW > 0 && imgH > 0 && panelW > 0 && panelH > 0) {
                        double scale = Math.min((double) panelW / imgW, (double) panelH / imgH);
                        int drawW = (int) (imgW * scale);
                        int drawH = (int) (imgH * scale);
                        int x = (panelW - drawW) / 2;
                        int y = (panelH - drawH) / 2;
    
                        g2d.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_SPEED);
                        g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                        g2d.drawImage(displayFrame, x, y, drawW, drawH, null);
    
                        displayVal.setText(imgW + "x" + imgH + "x32");
                    }
                    frameVal.setText(String.valueOf(bluelineFrame)); 
                } else {
                    // Placeholder text if no frame
                     g2d.setColor(Color.DARK_GRAY);
                     g2d.drawString("NO SIGNAL", getWidth()/2 - 30, getHeight()/2);
                }
            }
        };
        videoArea.setBackground(new Color(30,30,30));
        
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

    /**
     * Minimal VRAM prep - mostly legacy now as we draw direct.
     * Kept to satisfy FrameServer calls.
     */
    public void prepareVramFrame(BufferedImage img) {
        // No-op in direct draw mode
    }

    public void setRecycleCallback(Consumer<BufferedImage> callback) {
        this.recycleCallback = callback;
    }

    public void updateFrame(BufferedImage img) {
        // Simple swap
        BufferedImage old = this.displayFrame;
        this.displayFrame = img;
        
        // Recycle old frame immediately since we don't hold VRAM references anymore
        if (old != null && old != img && recycleCallback != null) {
            try {
                recycleCallback.accept(old);
            } catch (Exception e) { /* safe ignore */ }
        }
        
        // Trigger repaint to show new frame
        videoArea.repaint();
    }

    public void setFrameNumber(long frame) {
        this.bluelineFrame = frame;
        // Don't repaint just for frame number, updateFrame handles it essentially
        if (displayFrame == null) videoArea.repaint(); 
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
        projectVal.setText(props.getProjectRes());
        previewVal.setText(props.getPreviewRes());
        displayVal.setText(props.getDisplayRes());
        qualityVal.setText(props.getPreviewQuality());
        this.lowResPreview = props.isLowResPreview();
        repaint();
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
