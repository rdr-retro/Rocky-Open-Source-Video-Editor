package rocky.core.audio;

import javax.swing.*;
import javax.swing.plaf.basic.BasicSliderUI;
import java.awt.*;
import java.awt.event.*;
import java.awt.geom.RoundRectangle2D;

/**
 * MasterSoundPanel: Consola de audio profesional para Rocky Video Editor.
 * Incluye fader logarítmico, vúmetros estéreo con caída física y peak-hold.
 */
public class MasterSoundPanel extends JPanel {

    // --- Configuración Estética (Look & Feel) ---
    private final Color BG_COLOR = Color.decode("#0D0B14");
    private final Color METER_BG = Color.decode("#16141F");
    private final Color ACCENT_PURPLE = Color.decode("#9D50BB");
    private final Color TEXT_GRAY = Color.decode("#8E8E93");
    private final Color PEAK_RED = Color.decode("#FF4B5C");

    // --- Estado del Audio ---
    private float leftLevel = 0.0f;
    private float rightLevel = 0.0f;
    private float leftPeakHold = 0.0f;
    private float rightPeakHold = 0.0f;

    private final MeterBar leftBar, rightBar;
    private final JLabel lp, rp, curVolLabel;
    private final JSlider fader;

    public MasterSoundPanel() {
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(160, 450));
        setLayout(new BorderLayout(0, 15));
        setBorder(BorderFactory.createEmptyBorder(20, 12, 20, 12));

        // 1. HEADER: Lectura numérica de picos (Peak Meters)
        JPanel peakHeader = new JPanel(new GridLayout(1, 2, 4, 0));
        peakHeader.setOpaque(false);
        lp = createPeakLabel("-inf");
        rp = createPeakLabel("-inf");
        peakHeader.add(lp);
        peakHeader.add(rp);
        add(peakHeader, BorderLayout.NORTH);

        // 2. CENTER: El Mezclador (Fader + Vúmetros + Escala)
        JPanel mixerContainer = new JPanel(new BorderLayout(10, 0));
        mixerContainer.setOpaque(false);

        // Fader de volumen (Izquierda)
        fader = createFader();
        mixerContainer.add(fader, BorderLayout.WEST);

        // Grupo de medidores visuales (Centro)
        JPanel meterGroup = new JPanel(new GridLayout(1, 2, 3, 0));
        meterGroup.setOpaque(false);
        leftBar = new MeterBar();
        rightBar = new MeterBar();
        meterGroup.add(leftBar);
        meterGroup.add(rightBar);
        mixerContainer.add(meterGroup, BorderLayout.CENTER);

        // Escala de DB (Derecha)
        mixerContainer.add(createDBScale(), BorderLayout.EAST);

        add(mixerContainer, BorderLayout.CENTER);

        // 3. FOOTER: Indicador de volumen maestro
        curVolLabel = new JLabel("0.0 dB");
        curVolLabel.setForeground(Color.WHITE);
        curVolLabel.setFont(new Font("Monospaced", Font.BOLD, 13));
        curVolLabel.setHorizontalAlignment(SwingConstants.CENTER);
        add(curVolLabel, BorderLayout.SOUTH);

        // 4. ANIMACIÓN: Física de caída (Ballistics)
        // Simula la inercia de los vúmetros analógicos
        new Timer(25, e -> {
            leftLevel *= 0.82f;
            rightLevel *= 0.82f;
            leftPeakHold *= 0.97f;
            rightPeakHold *= 0.97f;
            repaint();
        }).start();
    }

    // --- MÉTODOS DE CONSTRUCCIÓN DE UI ---

    private JLabel createPeakLabel(String text) {
        JLabel l = new JLabel(text, SwingConstants.CENTER);
        l.setForeground(TEXT_GRAY);
        l.setFont(new Font("Monospaced", Font.BOLD, 10));
        l.setOpaque(true);
        l.setBackground(METER_BG);
        l.setBorder(BorderFactory.createLineBorder(BG_COLOR.brighter()));
        l.setPreferredSize(new Dimension(0, 22));
        return l;
    }

    private JPanel createDBScale() {
        JPanel p = new JPanel(new GridLayout(7, 1));
        p.setOpaque(false);
        String[] dbLabels = {"+12", "0", "-6", "-12", "-24", "-48", "-inf"};
        for (String s : dbLabels) {
            JLabel l = new JLabel(s);
            l.setForeground(TEXT_GRAY.darker());
            l.setFont(new Font("Inter", Font.PLAIN, 9));
            l.setVerticalAlignment(SwingConstants.TOP);
            p.add(l);
        }
        return p;
    }

    private JSlider createFader() {
        // CORRECCIÓN: 0 (Abajo/Mute) a 100 (Arriba/Max)
        JSlider s = new JSlider(JSlider.VERTICAL, 0, 100, 50); 
        s.setOpaque(false);
        s.setPreferredSize(new Dimension(32, 0));
        s.setUI(new ModernFaderUI(s));
        
        s.addChangeListener(e -> {
            float gain = getVolume();
            if (gain <= 0.0001f) {
                curVolLabel.setText("-inf dB");
            } else {
                double db = 20 * Math.log10(gain);
                curVolLabel.setText(String.format("%.1f dB", db));
            }
        });
        return s;
    }

    // --- API PÚBLICA (USADA POR AUDIOSERVER.JAVA) ---

    /**
     * Retorna el factor de ganancia. 
     * 0.0 = Silencio absoluto
     * 1.0 = Ganancia unidad (0dB) - ocurre al 50% del slider
     */
    public float getVolume() {
        float normalized = fader.getValue() / 50.0f; // 50 es el punto de 0dB
        return (float) Math.pow(normalized, 2); // Curva logarítmica
    }

    /**
     * Actualiza los niveles de los vúmetros en tiempo real
     */
    public void setLevels(float left, float right) {
        this.leftLevel = left;
        this.rightLevel = right;
        
        if (left > leftPeakHold) leftPeakHold = left;
        if (right > rightPeakHold) rightPeakHold = right;
        
        updatePeakText(lp, left);
        updatePeakText(rp, right);
        repaint();
    }

    private void updatePeakText(JLabel l, float val) {
        if (val <= 0.001) {
            l.setText("-inf");
            l.setForeground(TEXT_GRAY);
        } else {
            float db = (float)(20 * Math.log10(val));
            l.setText(String.format("%.1f", db));
            if (db > 0) l.setForeground(PEAK_RED);
            else if (db > -3) l.setForeground(Color.YELLOW);
            else l.setForeground(TEXT_GRAY);
        }
    }

    // --- COMPONENTES INTERNOS PERSONALIZADOS ---

    private class MeterBar extends JComponent {
        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int w = getWidth();
            int h = getHeight();
            float level = (this == leftBar) ? leftLevel : rightLevel;
            float peak = (this == leftBar) ? leftPeakHold : rightPeakHold;

            // Fondo del canal
            g2.setColor(METER_BG);
            g2.fillRoundRect(0, 0, w, h, 6, 6);

            // Relleno de volumen con gradiente profesional
            int fillH = (int) (h * Math.min(level, 1.2f) / 1.2f); // Normalizado a tope de escala
            if (fillH > 0) {
                LinearGradientPaint gp = new LinearGradientPaint(0, h, 0, 0,
                    new float[]{0.0f, 0.5f, 0.8f, 1.0f},
                    new Color[]{Color.GREEN, Color.GREEN, Color.YELLOW, PEAK_RED}
                );
                g2.setPaint(gp);
                g2.fillRoundRect(2, h - fillH, w - 4, fillH, 4, 4);
            }

            // Línea de Peak Hold (Pico máximo)
            if (peak > 0.001f) {
                int peakY = h - (int)(h * Math.min(peak, 1.2f) / 1.2f);
                g2.setColor(Color.WHITE);
                g2.fillRect(1, peakY, w - 2, 2);
            }
            g2.dispose();
        }
    }

    private class ModernFaderUI extends BasicSliderUI {
        public ModernFaderUI(JSlider b) { super(b); }

        @Override protected Dimension getThumbSize() { return new Dimension(26, 14); }

        @Override
        public void paintTrack(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            int cx = trackRect.x + trackRect.width / 2;
            g2.setColor(Color.BLACK);
            g2.fillRoundRect(cx - 2, trackRect.y, 4, trackRect.height, 2, 2);
            // Marcas de posición
            g2.setColor(BG_COLOR.brighter());
            for(int i=0; i<=10; i++) {
                int y = trackRect.y + (i * trackRect.height / 10);
                g2.drawLine(cx - 8, y, cx + 8, y);
            }
            g2.dispose();
        }

        @Override
        public void paintThumb(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            Rectangle r = thumbRect;
            
            // Cuerpo del Fader (Cromo oscuro)
            g2.setColor(Color.decode("#2C2C2C"));
            g2.fillRoundRect(r.x, r.y, r.width, r.height, 4, 4);
            
            // Indicador central brillante
            g2.setColor(ACCENT_PURPLE);
            g2.fillRect(r.x + 2, r.y + r.height/2 - 1, r.width - 4, 2);
            
            // Bordes y relieves
            g2.setColor(Color.WHITE.darker());
            g2.drawRoundRect(r.x, r.y, r.width, r.height, 4, 4);
            g2.dispose();
        }
    }
}