package rocky.core.audio;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

/**
 * A vertical panel for master audio control with dynamic gradient meters.
 * Replicates the provided UI with active (green) and idle (grey) states.
 */
public class MasterSoundPanel extends JPanel {
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color TEXT_COLOR = Color.decode("#dcd0ff");
    private final Color ACCENT_COLOR = Color.decode("#9d50bb");
    private final Color METER_BG = Color.decode("#1a0b2e");
    
    private float leftLevel = 0.0f;
    private float rightLevel = 0.0f;
    private float leftPeakHold = 0.0f;
    private float rightPeakHold = 0.0f;
    private long lastPeakUpdate = 0;

    private MeterBar leftBar, rightBar;
    private JLabel lp, rp, curVolLabel;
    private FaderPanel faderPanel;

    public MasterSoundPanel() {
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(160, 450));
        setLayout(new BorderLayout());
        setBorder(BorderFactory.createEmptyBorder(20, 15, 20, 15));

        // --- Header ---
        JPanel header = new JPanel(new BorderLayout());
        header.setBackground(BG_COLOR);
        JLabel title = new JLabel("MASTER", SwingConstants.CENTER);
        title.setForeground(ACCENT_COLOR);
        title.setFont(new Font("Inter", Font.BOLD, 10));
        header.add(title, BorderLayout.NORTH);
        
        JPanel peaks = new JPanel(new GridLayout(1, 2, 5, 0));
        peaks.setBackground(BG_COLOR);
        lp = createPeakLabel("-inf");
        rp = createPeakLabel("-inf");
        peaks.add(lp); peaks.add(rp);
        header.add(peaks, BorderLayout.CENTER);
        add(header, BorderLayout.NORTH);

        // --- Center Area (Fader + Meters) ---
        JPanel mainArea = new JPanel(new GridBagLayout());
        mainArea.setBackground(BG_COLOR);
        mainArea.setBorder(BorderFactory.createEmptyBorder(30, 0, 30, 0));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.BOTH;
        gbc.weighty = 1.0;

        // Fader (Left)
        faderPanel = new FaderPanel();
        gbc.gridx = 0; gbc.weightx = 0.3;
        mainArea.add(faderPanel, gbc);

        // Meters Container (Right)
        JPanel meterGroup = new JPanel(new GridBagLayout());
        meterGroup.setBackground(BG_COLOR);
        meterGroup.setBorder(BorderFactory.createEmptyBorder(0, 20, 0, 5));
        GridBagConstraints mgbc = new GridBagConstraints();
        mgbc.fill = GridBagConstraints.BOTH;
        mgbc.weighty = 1.0;

        leftBar = new MeterBar(true);
        mgbc.gridx = 0; mgbc.weightx = 0.35;
        meterGroup.add(leftBar, mgbc);

        JPanel scale = createDBScale();
        mgbc.gridx = 1; mgbc.weightx = 0.3;
        meterGroup.add(scale, mgbc);

        rightBar = new MeterBar(false);
        mgbc.gridx = 2; mgbc.weightx = 0.35;
        meterGroup.add(rightBar, mgbc);

        gbc.gridx = 1; gbc.weightx = 0.7;
        mainArea.add(meterGroup, gbc);

        add(mainArea, BorderLayout.CENTER);

        // --- Footer ---
        JPanel footer = new JPanel(new BorderLayout());
        footer.setBackground(BG_COLOR);
        curVolLabel = new JLabel("0.0 dB", SwingConstants.CENTER);
        curVolLabel.setForeground(TEXT_COLOR);
        curVolLabel.setFont(new Font("Monospaced", Font.BOLD, 11));
        footer.add(curVolLabel, BorderLayout.CENTER);
        add(footer, BorderLayout.SOUTH);

        // Timer for peak hold decay
        new Timer(50, e -> {
            if (System.currentTimeMillis() - lastPeakUpdate > 1500) {
                leftPeakHold *= 0.95f;
                rightPeakHold *= 0.95f;
                leftBar.repaint();
                rightBar.repaint();
            }
        }).start();
    }

    private JLabel createPeakLabel(String text) {
        JLabel l = new JLabel(text, SwingConstants.CENTER);
        l.setForeground(TEXT_COLOR);
        l.setFont(new Font("Monospaced", Font.BOLD, 10));
        l.setBackground(METER_BG);
        l.setOpaque(true);
        l.setBorder(BorderFactory.createLineBorder(Color.DARK_GRAY));
        return l;
    }

    private JPanel createDBScale() {
        JPanel p = new JPanel(new GridLayout(13, 1));
        p.setBackground(BG_COLOR);
        int[] values = {12, 6, 0, -3, -6, -9, -12, -18, -24, -30, -42, -54, -72};
        for (int v : values) {
            JLabel l = new JLabel(String.valueOf(v), SwingConstants.CENTER);
            l.setForeground(Color.GRAY);
            l.setFont(new Font("Dialog", Font.PLAIN, 8));
            p.add(l);
        }
        return p;
    }

    public void setLevels(float left, float right) {
        this.leftLevel = left;
        this.rightLevel = right;
        if (left > leftPeakHold) { leftPeakHold = left; lastPeakUpdate = System.currentTimeMillis(); }
        if (right > rightPeakHold) { rightPeakHold = right; lastPeakUpdate = System.currentTimeMillis(); }
        
        updatePeakText(lp, left);
        updatePeakText(rp, right);
        
        repaint();
    }

    private void updatePeakText(JLabel label, float level) {
        if (level <= 0) {
            label.setText("-inf");
            label.setForeground(TEXT_COLOR);
        } else {
            float db = (float)(20 * Math.log10(level));
            label.setText(String.format("%.1f", db));
            if (db > 0) label.setForeground(Color.RED);
            else if (db > -3) label.setForeground(Color.YELLOW);
            else label.setForeground(TEXT_COLOR);
        }
    }

    public float getVolume() {
        float val = 1.0f - faderPanel.faderValue;
        if (val < 0.05) return 0.0f;
        // Map 0.0-1.0 to a logarithmic scale that hits 1.0 at 0dB (approx 0.75 fader)
        return (float) Math.pow(val / 0.75f, 2.0);
    }

    private class MeterBar extends JPanel {
        private boolean isLeft;
        public MeterBar(boolean left) { this.isLeft = left; setOpaque(false); }
        
        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g;
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            int w = getWidth();
            int h = getHeight();
            float level = isLeft ? leftLevel : rightLevel;
            float peak = isLeft ? leftPeakHold : rightPeakHold;

            // Background
            g2.setColor(METER_BG);
            g2.fillRect(0, 0, w, h);

            // Draw segments
            int segments = 60;
            int gap = 1;
            int segH = (h / segments) - gap;
            
            for (int i = 0; i < segments; i++) {
                float segLevel = 1.0f - ((float)i / segments);
                float db = (float)(20 * Math.log10(segLevel));
                
                Color c;
                if (db > 0) c = Color.RED;
                else if (db > -6) c = Color.YELLOW;
                else c = Color.GREEN;
                
                if (segLevel <= level) {
                    g2.setColor(c);
                } else {
                    g2.setColor(c.darker().darker().darker());
                }
                g2.fillRect(2, i * (segH + gap), w - 4, segH);
            }

            // Peak Hold line
            if (peak > 0) {
                int peakY = h - (int)(h * peak);
                g2.setColor(Color.WHITE);
                g2.fillRect(0, peakY, w, 2);
            }
        }
    }

    private class FaderPanel extends JPanel {
        private float faderValue = 0.25f; // Starts at 0dB approx
        private boolean dragging = false;

        public FaderPanel() {
            setOpaque(false);
            MouseAdapter ma = new MouseAdapter() {
                @Override public void mousePressed(MouseEvent e) { update(e.getY()); dragging = true; }
                @Override public void mouseReleased(MouseEvent e) { dragging = false; }
                @Override public void mouseDragged(MouseEvent e) { update(e.getY()); }
                private void update(int y) {
                    float val = (float)y / getHeight();
                    faderValue = Math.min(1.0f, Math.max(0.0f, val));
                    float db = (float)(20 * Math.log10(getVolume()));
                    curVolLabel.setText(String.format("%.1f dB", db));
                    repaint();
                }
            };
            addMouseListener(ma); addMouseMotionListener(ma);
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g;
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            
            int w = getWidth();
            int h = getHeight();
            int cx = w / 2;

            // Track
            g2.setColor(Color.BLACK);
            g2.fillRect(cx - 2, 10, 4, h - 20);
            g2.setColor(Color.DARK_GRAY);
            g2.drawRect(cx - 2, 10, 4, h - 20);

            // Handle
            int hy = (int)(faderValue * h);
            int hw = 26;
            int hh = 14;
            
            // Drop shadow
            g2.setColor(new Color(0,0,0,100));
            g2.fillRect(cx - hw/2 + 2, hy - hh/2 + 2, hw, hh);

            // Silver body
            GradientPaint gp = new GradientPaint(cx - hw/2, hy, Color.LIGHT_GRAY, cx + hw/2, hy, Color.GRAY);
            g2.setPaint(gp);
            g2.fillRect(cx - hw/2, hy - hh/2, hw, hh);
            
            // Detail lines
            g2.setColor(Color.BLACK);
            g2.drawLine(cx - hw/2, hy, cx + hw/2, hy);
            g2.drawRect(cx - hw/2, hy - hh/2, hw, hh);
        }
    }
}
