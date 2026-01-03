package rocky.core.audio;

import javax.swing.*;
import javax.swing.plaf.basic.BasicSliderUI;
import java.awt.*;
import java.awt.event.*;
import java.awt.geom.RoundRectangle2D;

/**
 * Panel maestro de audio con fader logarítmico y medidores estéreo.
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
    private JSlider fader;

    public MasterSoundPanel() {
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(180, 480));
        setLayout(new BorderLayout());
        setBorder(BorderFactory.createEmptyBorder(20, 15, 20, 15));

        // ---------- HEADER ----------
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
        peaks.add(lp);
        peaks.add(rp);
        header.add(peaks, BorderLayout.CENTER);

        add(header, BorderLayout.NORTH);

        // ---------- CENTRO: FADER + METERS ----------
        JPanel mainArea = new JPanel(new GridBagLayout());
        mainArea.setBackground(BG_COLOR);
        mainArea.setBorder(BorderFactory.createEmptyBorder(25, 0, 25, 0));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.BOTH;
        gbc.weighty = 1.0;

        // FADER (izquierda)
        fader = createFader();
        JPanel faderWrapper = new JPanel(new BorderLayout());
        faderWrapper.setBackground(BG_COLOR);
        faderWrapper.add(fader, BorderLayout.CENTER);
        gbc.gridx = 0;
        gbc.weightx = 0.30;
        gbc.insets = new Insets(0, 0, 0, 5);
        mainArea.add(faderWrapper, gbc);

        // Grupo de medidores (derecha)
        JPanel meterGroup = new JPanel(new GridBagLayout());
        meterGroup.setBackground(BG_COLOR);
        meterGroup.setBorder(BorderFactory.createEmptyBorder(0, 10, 0, 0));
        GridBagConstraints mgbc = new GridBagConstraints();
        mgbc.fill = GridBagConstraints.BOTH;
        mgbc.weighty = 1.0;

        leftBar = new MeterBar(true);
        mgbc.gridx = 0;
        mgbc.weightx = 0.35;
        mgbc.insets = new Insets(0, 0, 0, 0);
        meterGroup.add(leftBar, mgbc);

        JPanel scale = createDBScale();
        mgbc.gridx = 1;
        mgbc.weightx = 0.3;
        mgbc.insets = new Insets(8, 4, 8, 4);
        meterGroup.add(scale, mgbc);

        rightBar = new MeterBar(false);
        mgbc.gridx = 2;
        mgbc.weightx = 0.35;
        mgbc.insets = new Insets(0, 0, 0, 0);
        meterGroup.add(rightBar, mgbc);

        gbc.gridx = 1;
        gbc.weightx = 0.70;
        gbc.insets = new Insets(0, 10, 0, 0);
        mainArea.add(meterGroup, gbc);

        add(mainArea, BorderLayout.CENTER);

        // ---------- FOOTER ----------
        JPanel footer = new JPanel(new BorderLayout());
        footer.setBackground(BG_COLOR);
        curVolLabel = new JLabel("0.0 dB", SwingConstants.CENTER);
        curVolLabel.setForeground(TEXT_COLOR);
        curVolLabel.setFont(new Font("Monospaced", Font.BOLD, 11));
        footer.add(curVolLabel, BorderLayout.CENTER);
        add(footer, BorderLayout.SOUTH);

        // Timer para decaimiento del peak hold
        new Timer(50, e -> {
            long now = System.currentTimeMillis();
            if (now - lastPeakUpdate > 1500) {
                leftPeakHold *= 0.95f;
                rightPeakHold *= 0.95f;
                if (leftPeakHold < 0.001f)
                    leftPeakHold = 0;
                if (rightPeakHold < 0.001f)
                    rightPeakHold = 0;
                leftBar.repaint();
                rightBar.repaint();
            }
        }).start();
    }

    // ---------- UIF UNITS ----------

    private JLabel createPeakLabel(String text) {
        JLabel l = new JLabel(text, SwingConstants.CENTER);
        l.setForeground(TEXT_COLOR);
        l.setFont(new Font("Monospaced", Font.BOLD, 10));
        l.setBackground(METER_BG);
        l.setOpaque(true);
        l.setBorder(BorderFactory.createLineBorder(new Color(40, 40, 60)));
        return l;
    }

    private JPanel createDBScale() {
        JPanel p = new JPanel(new GridLayout(13, 1));
        p.setBackground(BG_COLOR);
        int[] values = { 12, 6, 0, -3, -6, -9, -12, -18, -24, -30, -42, -54, -72 };
        for (int v : values) {
            JLabel l = new JLabel(String.valueOf(v), SwingConstants.CENTER);
            l.setForeground(new Color(140, 140, 160));
            l.setFont(new Font("Inter", Font.PLAIN, 9));
            p.add(l);
        }
        return p;
    }

    private JSlider createFader() {
        // 0 = abajo (mute), 100 = arriba (max)
        JSlider slider = new JSlider(JSlider.VERTICAL, 0, 100, 25);
        slider.setOpaque(false);
        slider.setPaintTicks(false);
        slider.setPaintLabels(false);
        slider.setFocusable(false);
        slider.setBorder(BorderFactory.createEmptyBorder(8, 0, 8, 0));

        slider.setUI(new CustomFaderUI(slider)); // UI personalizado

        slider.addChangeListener(e -> {
            float v = 1.0f - (slider.getValue() / 100f);
            float volume = mapToLogVolume(v);
            float db;
            if (volume <= 0.0001f) {
                db = -120f;
                curVolLabel.setText("-inf dB");
            } else {
                db = (float) (20 * Math.log10(volume));
                if (db < -60f) {
                    curVolLabel.setText("-inf dB");
                } else {
                    curVolLabel.setText(String.format("%.1f dB", db));
                }
            }
        });

        return slider;
    }

    // Mapear 0..1 a volumen logarítmico
    private float mapToLogVolume(float val) {
        if (val < 0.05f)
            return 0.0f;
        return (float) Math.pow(val / 0.75f, 2.0);
    }

    // ---------- API PÚBLICA PARA EL AUDIO ----------

    public void setLevels(float left, float right) {
        this.leftLevel = clamp01(left);
        this.rightLevel = clamp01(right);

        if (left > leftPeakHold) {
            leftPeakHold = left;
            lastPeakUpdate = System.currentTimeMillis();
        }
        if (right > rightPeakHold) {
            rightPeakHold = right;
            lastPeakUpdate = System.currentTimeMillis();
        }

        updatePeakText(lp, this.leftLevel);
        updatePeakText(rp, this.rightLevel);

        repaint();
    }

    public float getVolume() {
        float v = 1.0f - (fader.getValue() / 100f);
        return mapToLogVolume(v);
    }

    private float clamp01(float v) {
        if (v < 0f)
            return 0f;
        if (v > 1f)
            return 1f;
        return v;
    }

    private void updatePeakText(JLabel label, float level) {
        if (level <= 0.0001f) {
            label.setText("-inf");
            label.setForeground(TEXT_COLOR);
        } else {
            float db = (float) (20 * Math.log10(level));
            db = Math.max(db, -60f);
            label.setText(String.format("%.1f", db));
            if (db > 0) {
                label.setForeground(Color.RED);
            } else if (db > -3) {
                label.setForeground(Color.YELLOW);
            } else {
                label.setForeground(TEXT_COLOR);
            }
        }
    }

    // ================== CLASE METERBAR ==================

    private class MeterBar extends JPanel {
        private final boolean isLeft;

        public MeterBar(boolean left) {
            this.isLeft = left;
            setOpaque(false);
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int w = getWidth();
            int h = getHeight();

            float level = isLeft ? leftLevel : rightLevel;
            float peak = isLeft ? leftPeakHold : rightPeakHold;

            // Fondo con esquinas redondeadas
            int arc = 10;
            Shape bg = new RoundRectangle2D.Float(0, 0, w - 1, h - 1, arc, arc);
            g2.setColor(METER_BG);
            g2.fill(bg);
            g2.setColor(METER_BG.darker());
            g2.draw(bg);

            // Segmentos
            int segments = 60;
            int gap = 1;
            int top = 4;
            int bottom = 4;
            int usableH = h - top - bottom;
            if (usableH <= 0) {
                g2.dispose();
                return;
            }
            int segH = usableH / segments - gap;
            if (segH < 1)
                segH = 1;

            for (int i = 0; i < segments; i++) {
                float segLevel = 1.0f - ((float) i / segments);
                float db = (float) (20 * Math.log10(segLevel));

                Color c;
                if (db > 0)
                    c = Color.RED;
                else if (db > -6)
                    c = Color.YELLOW;
                else
                    c = Color.GREEN;

                int y = top + i * (segH + gap);

                if (segLevel <= level) {
                    g2.setColor(c);
                } else {
                    // Idle: tono oscuro neutro
                    g2.setColor(new Color(25, 30, 40));
                }
                g2.fillRoundRect(3, y, w - 6, segH, 4, 4);
            }

            // Peak hold line
            if (peak > 0.0f) {
                int peakY = h - bottom - (int) (usableH * peak);
                // brillo central
                g2.setColor(new Color(255, 255, 255, 200));
                g2.fillRect(1, peakY, w - 2, 2);
                // sombra ligera
                g2.setColor(new Color(0, 0, 0, 80));
                g2.drawLine(1, peakY + 2, w - 2, peakY + 2);
            }

            g2.dispose();
        }
    }

    // ================== CUSTOM FADER UI (JSLIDER) ==================

    /**
     * UI personalizada para el fader (JSlider vertical).
     * Basada en BasicSliderUI, cambiando track y thumb.
     */
    private static class CustomFaderUI extends BasicSliderUI {

        private boolean hover = false;
        private boolean pressed = false;

        public CustomFaderUI(JSlider slider) {
            super(slider);
            slider.addMouseListener(new MouseAdapter() {
                @Override
                public void mouseEntered(MouseEvent e) {
                    hover = true;
                    slider.repaint();
                }

                @Override
                public void mouseExited(MouseEvent e) {
                    hover = false;
                    slider.repaint();
                }

                @Override
                public void mousePressed(MouseEvent e) {
                    pressed = true;
                    slider.repaint();
                }

                @Override
                public void mouseReleased(MouseEvent e) {
                    pressed = false;
                    slider.repaint();
                }
            });
        }

        @Override
        protected Dimension getThumbSize() {
            return new Dimension(28, 16);
        }

        @Override
        public void paintTrack(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int cx = trackRect.x + trackRect.width / 2;
            int top = trackRect.y + 4;
            int bottom = trackRect.y + trackRect.height - 4;
            int trackWidth = 4;

            // Canal negro con borde gris
            g2.setColor(Color.BLACK);
            g2.fillRoundRect(cx - trackWidth / 2, top, trackWidth, bottom - top, 6, 6);
            g2.setColor(Color.DARK_GRAY);
            g2.drawRoundRect(cx - trackWidth / 2, top, trackWidth, bottom - top, 6, 6);

            g2.dispose();
        }

        @Override
        public void paintThumb(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            Rectangle r = thumbRect;

            int hw = r.width;
            int hh = r.height;
            int x = r.x;
            int y = r.y;

            // Sombra
            g2.setColor(new Color(0, 0, 0, 100));
            g2.fillRoundRect(x + 2, y + 2, hw, hh, 6, 6);

            // Colores según estado
            Color c1, c2;
            if (pressed) {
                c1 = new Color(220, 220, 220);
                c2 = new Color(110, 110, 110);
            } else if (hover) {
                c1 = new Color(240, 240, 240);
                c2 = new Color(130, 130, 130);
            } else {
                c1 = Color.LIGHT_GRAY;
                c2 = Color.GRAY;
            }

            GradientPaint gp = new GradientPaint(
                    x, y, c1,
                    x + hw, y, c2);
            g2.setPaint(gp);
            g2.fillRoundRect(x, y, hw, hh, 6, 6);

            // Detalle central
            g2.setColor(Color.BLACK);
            g2.drawRoundRect(x, y, hw, hh, 6, 6);
            g2.drawLine(x + 3, y + hh / 2, x + hw - 3, y + hh / 2);

            g2.dispose();
        }
    }

    // ================== TEST MAIN OPCIONAL ==================

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JFrame f = new JFrame("MasterSoundPanel Demo");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            MasterSoundPanel panel = new MasterSoundPanel();
            f.add(panel);
            f.pack();
            f.setLocationRelativeTo(null);
            f.setVisible(true);

            // Simulación de niveles para probar UI
            new Timer(50, e -> {
                float left = (float) Math.abs(Math.sin(System.currentTimeMillis() / 400.0));
                float right = (float) Math.abs(Math.cos(System.currentTimeMillis() / 500.0));
                panel.setLevels(left, right);
            }).start();
        });
    }
}
