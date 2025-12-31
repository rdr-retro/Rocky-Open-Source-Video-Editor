package a.mastersound;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * A vertical panel for master audio control with dynamic gradient meters.
 * Replicates the provided UI with active (green) and idle (grey) states.
 */
public class MasterSoundPanel extends JPanel {
    private final Color BG_COLOR = Color.decode("#1a1a1a");
    private final Color TEXT_COLOR = Color.decode("#cccccc");
    private final Color VALUE_BLUE = Color.decode("#5fbcd3");
    private final Color DB_BLUE = Color.decode("#4e8fb2");
    
    private float leftLevel = 0.0f;  // 0.0 to 1.0 (Idle)
    private float rightLevel = 0.0f;
    private float leftPeak = -7.7f;
    private float rightPeak = -6.0f;

    private JLabel lp, rp; // Peak labels

    public MasterSoundPanel() {
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(100, 400));
        setLayout(new BorderLayout());
        setBorder(BorderFactory.createEmptyBorder(2, 2, 2, 2));

        // --- Header Section ---
        JPanel header = new JPanel(new FlowLayout(FlowLayout.CENTER, 2, 0));
        header.setBackground(BG_COLOR);
        JLabel iconL = new JLabel("▣");
        iconL.setForeground(Color.WHITE);
        iconL.setFont(new Font("Monospaced", Font.BOLD, 14));
        JLabel title = new JLabel("Master");
        title.setForeground(TEXT_COLOR);
        title.setFont(new Font("Inter", Font.PLAIN, 12));
        header.add(iconL);
        header.add(title);

        // --- Toolbar Section ---
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.CENTER, 4, 0));
        toolbar.setBackground(BG_COLOR);
        JLabel fxLabel = new JLabel("fx");
        fxLabel.setForeground(TEXT_COLOR);
        fxLabel.setFont(new Font("Serif", Font.ITALIC, 16));
        toolbar.add(fxLabel);

        JPanel topSection = new JPanel();
        topSection.setLayout(new BoxLayout(topSection, BoxLayout.Y_AXIS));
        topSection.setBackground(BG_COLOR);
        topSection.add(header);
        topSection.add(toolbar);
        add(topSection, BorderLayout.NORTH);

        // --- Main Control Area ---
        JPanel mainArea = new JPanel(new BorderLayout());
        mainArea.setBackground(BG_COLOR);
        mainArea.setBorder(BorderFactory.createEmptyBorder(5, 0, 5, 0));

        // 1. Fader track
        faderPanel = new FaderPanel();
        // mainArea.add(faderTrack, BorderLayout.WEST); // Removed to bundle with meters

        // 2 & 3. dB scale and meters combined
        JPanel meterContainer = new JPanel(new GridBagLayout());
        meterContainer.setBackground(BG_COLOR);
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.BOTH;
        gbc.weighty = 1.0;

        // Peak labels at the very top of meters
        JPanel peakPanel = new JPanel(new GridLayout(1, 3));
        peakPanel.setBackground(BG_COLOR);
        lp = new JLabel("-7.7", SwingConstants.CENTER);
        lp.setForeground(TEXT_COLOR); lp.setFont(new Font("Dialog", Font.PLAIN, 9));
        JLabel mp = new JLabel(""); // space
        rp = new JLabel("-6.0", SwingConstants.CENTER);
        rp.setForeground(TEXT_COLOR); rp.setFont(new Font("Dialog", Font.PLAIN, 9));
        peakPanel.add(lp); peakPanel.add(mp); peakPanel.add(rp);
        
        // Wrap metrics in a container that has peaks at top
        JPanel centerWrapper = new JPanel(new BorderLayout());
        centerWrapper.setBackground(BG_COLOR);
        centerWrapper.add(peakPanel, BorderLayout.NORTH);

        JPanel metersAndScale = new JPanel(new GridBagLayout());
        metersAndScale.setBackground(BG_COLOR);
        
        MeterBar leftBar = new MeterBar(true);
        gbc.gridx = 0; gbc.weightx = 0.3;
        metersAndScale.add(leftBar, gbc);

        JPanel dbLabels = new JPanel(new GridLayout(19, 1));
        dbLabels.setBackground(BG_COLOR);
        for (int i = 1; i <= 19; i++) {
            JLabel l = new JLabel("- " + (i * 3) + " -", SwingConstants.CENTER);
            l.setForeground(DB_BLUE);
            l.setFont(new Font("Dialog", Font.PLAIN, 10));
            dbLabels.add(l);
        }
        gbc.gridx = 1; gbc.weightx = 0.4;
        metersAndScale.add(dbLabels, gbc);

        MeterBar rightBar = new MeterBar(false);
        gbc.gridx = 2; gbc.weightx = 0.3;
        metersAndScale.add(rightBar, gbc);

        centerWrapper.add(metersAndScale, BorderLayout.CENTER);
        
        // --- Bundle Fader and Meters Together ---
        JPanel bundledControls = new JPanel(new BorderLayout());
        bundledControls.setBackground(BG_COLOR);
        bundledControls.add(faderPanel, BorderLayout.WEST);
        bundledControls.add(centerWrapper, BorderLayout.CENTER);

        JPanel centeringWrapper = new JPanel(new FlowLayout(FlowLayout.CENTER, 0, 0));
        centeringWrapper.setBackground(BG_COLOR);
        centeringWrapper.add(bundledControls);

        mainArea.add(centeringWrapper, BorderLayout.CENTER);
        
        add(mainArea, BorderLayout.CENTER);

        // --- Footer ---
        JPanel footer = new JPanel(new FlowLayout(FlowLayout.CENTER, 5, 0));
        footer.setBackground(BG_COLOR);
        JLabel v1 = new JLabel("0,0");
        v1.setForeground(VALUE_BLUE); v1.setFont(new Font("Dialog", Font.BOLD, 11));
        JLabel v2 = new JLabel("0,0");
        v2.setForeground(VALUE_BLUE); v2.setFont(new Font("Dialog", Font.BOLD, 11));
        footer.add(v1); footer.add(Box.createHorizontalStrut(10)); footer.add(v2);
        add(footer, BorderLayout.SOUTH);
    }

    public void setLevels(float left, float right) {
        this.leftLevel = left;
        this.rightLevel = right;
        
        // Dynamic peaks (simulated DB mapping)
        if (left > 0) {
            float db = (float)(20 * Math.log10(left));
            if (db > leftPeak) {
                leftPeak = db;
                lp.setText(String.format("%.1f", db));
            }
        }
        if (right > 0) {
            float db = (float)(20 * Math.log10(right));
            if (db > rightPeak) {
                rightPeak = db;
                rp.setText(String.format("%.1f", db));
            }
        }
        
        repaint();
    }

    /**
     * Returns the current master gain multiplier.
     * Uses a logarithmic curve for natural volume feeling.
     * 0.0 at bottom, 1.0 at Roughly 66%, and up to 1.5x at top for headroom.
     */
    public float getVolume() {
        if (faderPanel == null) return 1.0f;
        float val = 1.0f - faderPanel.faderValue; // Inverted: 1.0 at top
        if (val < 0.01f) return 0.0f;
        // Exponential curve for more natural response
        return (float) (Math.pow(val, 2) * 1.5);
    }

    private FaderPanel faderPanel;

    private class MeterBar extends JPanel {
        private boolean isLeft;
        public MeterBar(boolean left) { this.isLeft = left; setOpaque(false); }
        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2d = (Graphics2D) g;
            int w = getWidth();
            int h = getHeight();
            float level = isLeft ? leftLevel : rightLevel;

            // Background (Idle Gray)
            g2d.setColor(Color.decode("#2a2a2a"));
            g2d.fillRect(2, 0, w - 4, h);

            if (level > 0) {
                int barH = (int)(h * level);
                int barY = h - barH;
                
                // Gradient for signal (Green to Yellow)
                GradientPaint gp = new GradientPaint(0, h, Color.GREEN, 0, 0, Color.YELLOW);
                g2d.setPaint(gp);
                g2d.fillRect(2, barY, w - 4, barH);
                
                // Overlay darker lines for scale effect
                g2d.setColor(new Color(0,0,0,50));
                for(int i=0; i<h; i+=4) g2d.drawLine(2, i, w-2, i);
            }
        }
    }

    private class FaderPanel extends JPanel {
        private float faderValue = 0.43f;
        private boolean dragging = false;
        public FaderPanel() {
            setOpaque(false);
            setPreferredSize(new Dimension(35, 0));
            MouseAdapter ma = new MouseAdapter() {
                @Override public void mousePressed(MouseEvent e) { updateFader(e.getY()); dragging = true; }
                @Override public void mouseReleased(MouseEvent e) { dragging = false; }
                @Override public void mouseDragged(MouseEvent e) { updateFader(e.getY()); }
                private void updateFader(int y) {
                    int margin = 30;
                    int trackH = getHeight() - (2 * margin);
                    if (trackH <= 0) return;
                    faderValue = (float)(y - margin) / trackH;
                    if (faderValue < 0) faderValue = 0; if (faderValue > 1) faderValue = 1;
                    repaint();
                }
            };
            addMouseListener(ma); addMouseMotionListener(ma);
        }
        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2d = (Graphics2D) g;
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            int centerX = getWidth() / 2 + 5;
            int margin = 30;
            g2d.setColor(Color.decode("#333333"));
            g2d.drawLine(centerX, margin, centerX, getHeight() - margin);
            int trackH = getHeight() - (2 * margin);
            int handleY = margin + (int)(faderValue * trackH);
            g2d.setColor(Color.WHITE);
            int sw = 7, sh = 5, gap = 1;
            g2d.fillRect(centerX - sw - gap, handleY - sh - gap, sw, sh);
            g2d.fillRect(centerX + gap, handleY - sh - gap, sw, sh);
            g2d.fillRect(centerX - sw - gap, handleY + gap, sw, sh);
            g2d.fillRect(centerX + gap, handleY + gap, sw, sh);
            g2d.drawLine(centerX - 10, handleY, centerX + 10, handleY);
        }
    }
}
