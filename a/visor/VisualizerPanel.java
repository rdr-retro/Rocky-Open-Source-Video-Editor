package a.visor;

import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.event.MouseEvent;

/**
 * A panel that acts as a video visualizer (Part A Right).
 * Replicated to match the provided reference image.
 */
public class VisualizerPanel extends JPanel {
    private final Color ACCENT_RED = Color.decode("#FF6B6B");
    private final Color PANEL_BG = Color.decode("#1e1e1e");
    private final Color CONTROL_BG = Color.decode("#404040");
    private final Color TEXT_COLOR = Color.decode("#cccccc");

    private JLabel projectVal;
    private JLabel previewVal;
    private JLabel displayVal;
    private JLabel frameVal;

    private JPanel videoArea;
    private JLabel frameDisplayLabel;
    private BufferedImage currentFrame;
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
                if (currentFrame != null) {
                    Graphics2D g2d = (Graphics2D) g;
                    
                    if (lowResPreview) {
                        g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
                    } else {
                        g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                    }
                    
                    int panelW = getWidth();
                    int panelH = getHeight();
                    int imgW = currentFrame.getWidth();
                    int imgH = currentFrame.getHeight();
                    
                    double scale = Math.min((double)panelW / imgW, (double)panelH / imgH);
                    int drawW = (int)(imgW * scale);
                    int drawH = (int)(imgH * scale);
                    int x = (panelW - drawW) / 2;
                    int y = (panelH - drawH) / 2;
                    
                    g2d.drawImage(currentFrame, x, y, drawW, drawH, null);
                }
            }
        };
        videoArea.setBackground(Color.BLACK);
        
        frameDisplayLabel = new JLabel("", SwingConstants.CENTER);
        frameDisplayLabel.setForeground(ACCENT_RED);
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
        
        playBar.add(createIconButton("▶", e -> { if(onPlay != null) onPlay.run(); })); // Play
        playBar.add(createIconButton("⏸", e -> { if(onPause != null) onPause.run(); })); // Pause
        playBar.add(createIconButton("■", e -> { if(onStop != null) onStop.run(); })); // Stop
        playBar.add(createIconButton("≡", null)); // Menu
        
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
        leftCol.add(createStatusLine("Vista previa:", previewVal, ACCENT_RED));
        statusPanel.add(leftCol);

        // Column Right
        JPanel rightCol = new JPanel();
        rightCol.setLayout(new BoxLayout(rightCol, BoxLayout.Y_AXIS));
        rightCol.setBackground(PANEL_BG);
        
        frameVal = new JLabel("59");
        rightCol.add(createStatusLine("Fotograma:", frameVal, Color.WHITE));
        
        rightCol.add(Box.createVerticalStrut(2));
        
        displayVal = new JLabel("597x336x32");
        rightCol.add(createStatusLine("Visualización:", displayVal, ACCENT_RED));
        statusPanel.add(rightCol);

        southContainer.add(statusPanel);

        // 3. Tab Bar
        JPanel tabBar = new JPanel();
        tabBar.setLayout(new FlowLayout(FlowLayout.LEFT, 0, 0));
        tabBar.setBackground(Color.decode("#252525"));
        tabBar.setMaximumSize(new Dimension(Integer.MAX_VALUE, 30));
        tabBar.setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, Color.BLACK));

        tabBar.add(createTab("Vista previa de vídeo", true));
        
        southContainer.add(tabBar);

        add(southContainer, BorderLayout.SOUTH);
    }

    public void updateFrame(BufferedImage img) {
        this.currentFrame = img;
        videoArea.repaint();
    }

    private JLabel createIconButton(String icon, java.util.function.Consumer<MouseEvent> onClick) {
        JLabel label = new JLabel(icon);
        label.setForeground(Color.WHITE);
        label.setFont(new Font("Monospaced", Font.BOLD, 22));
        label.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        if (onClick != null) {
            label.addMouseListener(new java.awt.event.MouseAdapter() {
                @Override
                public void mousePressed(java.awt.event.MouseEvent e) {
                    onClick.accept(e);
                }
            });
        }
        return label;
    }

    public void setOnPlay(Runnable r) { this.onPlay = r; }
    public void setOnPause(Runnable r) { this.onPause = r; }
    public void setOnStop(Runnable r) { this.onStop = r; }

    public void displayFrame(String info) {
        frameDisplayLabel.setText(info);
        videoArea.repaint();
    }

    public void updateProperties(b.timeline.ProjectProperties props) {
        projectVal.setText(props.getProjectRes());
        previewVal.setText(props.getPreviewRes());
        displayVal.setText(props.getDisplayRes());
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
        tab.setBackground(selected ? PANEL_BG : Color.decode("#252525"));
        tab.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.BLACK));
        
        JLabel label = new JLabel(title);
        label.setForeground(selected ? Color.WHITE : Color.GRAY);
        label.setFont(new Font("Inter", Font.PLAIN, 11));
        
        if (selected) {
             // Add mini close/options icons like in image
             JLabel icons = new JLabel(" ▢ ✕ ");
             icons.setForeground(Color.LIGHT_GRAY);
             icons.setFont(new Font("Monospaced", Font.PLAIN, 10));
             tab.add(label);
             tab.add(icons);
        } else {
             tab.add(label);
        }
        
        return tab;
    }
}
