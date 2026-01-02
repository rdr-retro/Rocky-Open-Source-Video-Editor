package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;

public class BottomBarPanel extends JPanel {
    private final Color BG_COLOR = Color.decode("#1a0b2e"); 
    private final Color TEXT_COLOR = Color.decode("#dcd0ff");

    private JLabel speedLabel;
    private JSlider speedSlider;
    private java.util.function.Consumer<Double> onRateChange;
    private TimelinePanel timeline;
    
    public BottomBarPanel() {
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(800, 30));
        setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, Color.BLACK)); // Top border

        // LEFT SECTION: Velocity
        JPanel leftPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 5));
        leftPanel.setOpaque(false);
        
        speedLabel = new JLabel("Velocidad: 1,00");
        speedLabel.setForeground(TEXT_COLOR);
        speedLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        
        // Range: -4.00 to 4.00 (x100 for integer resolution)
        speedSlider = new JSlider(-400, 400, 100);
        speedSlider.setPreferredSize(new Dimension(100, 20));
        speedSlider.setOpaque(false);
        
        speedSlider.addChangeListener(e -> {
            double rate = speedSlider.getValue() / 100.0;
            speedLabel.setText(String.format("Velocidad: %.2f", rate));
            if (onRateChange != null) onRateChange.accept(rate);
        });

        speedSlider.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override
            public void mouseClicked(java.awt.event.MouseEvent e) {
                if (e.getClickCount() == 2) {
                    speedSlider.setValue(100); // Snap to 1.00 on double click
                }
            }
            @Override
            public void mouseReleased(java.awt.event.MouseEvent e) {
                // Return to 1.00x (Normal Speed) on release
                speedSlider.setValue(100); 
            }
        });

        // Precision Dragging Logic
        speedSlider.addMouseMotionListener(new java.awt.event.MouseAdapter() {
            private int lastX = -1;
            @Override
            public void mouseDragged(java.awt.event.MouseEvent e) {
                if (e.isControlDown() || e.isMetaDown()) {
                    // Logic for high precision skipped here as JSlider is hard to override 
                    // without a custom UI, but we can potentially "slow down" the value change 
                    // or just leave the default feel for now. Standard JSlider is already granular.
                }
            }
        });
        
        leftPanel.add(speedLabel);
        leftPanel.add(speedSlider);
        
        // CENTER SECTION: Playback Controls
        JPanel centerPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 5, 2));
        centerPanel.setOpaque(false);
        
        // Buttons (using text symbols for simplicity, ideally icons)
        // Record, Start, Prev, Play, Next, End
        String[] icons = {"●", "|<", "<", "►", ">", ">|"};
        for (String icon : icons) {
            JButton btn = new JButton(icon);
            btn.setMargin(new Insets(0, 4, 0, 4));
            btn.setFocusPainted(false);
            btn.setContentAreaFilled(false);
            btn.setBorderPainted(false);
            btn.setForeground(TEXT_COLOR);
            if (icon.equals("●")) btn.setForeground(Color.decode("#ff4757")); // Vibrant red record
            centerPanel.add(btn);
        }

        // RIGHT SECTION: Timecode & Rec Info
        JPanel rightPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 15, 5));
        rightPanel.setOpaque(false);
        
        JLabel timeLabel = new JLabel("00:00:00;00");
        timeLabel.setForeground(TEXT_COLOR);
        timeLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        
        JLabel recTimeLabel = new JLabel("Tiempo de grabación (2 canales): 43:00:55");
        recTimeLabel.setForeground(TEXT_COLOR);
        recTimeLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        
        rightPanel.add(timeLabel);
        rightPanel.add(recTimeLabel);

        add(leftPanel, BorderLayout.WEST);
        add(centerPanel, BorderLayout.CENTER);
        add(rightPanel, BorderLayout.EAST);
    }

    public void setOnRateChange(java.util.function.Consumer<Double> callback) {
        this.onRateChange = callback;
    }

    public void setRate(double rate) {
        int val = (int)(rate * 100);
        if (val < -400) val = -400;
        if (val > 400) val = 400;
        speedSlider.setValue(val);
    }
}
