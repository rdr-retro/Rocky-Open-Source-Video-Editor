package b.timeline;

import javax.swing.*;
import java.awt.*;

public class BottomBarPanel extends JPanel {
    private final Color BG_COLOR = Color.decode("#2d2d2d"); // Dark gray background
    private final Color TEXT_COLOR = Color.decode("#b0b0b0");
    
    public BottomBarPanel() {
        setLayout(new BorderLayout());
        setBackground(BG_COLOR);
        setPreferredSize(new Dimension(800, 30));
        setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, Color.BLACK)); // Top border

        // LEFT SECTION: Velocity
        JPanel leftPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 5));
        leftPanel.setOpaque(false);
        
        JLabel speedLabel = new JLabel("Velocidad: 0,00");
        speedLabel.setForeground(TEXT_COLOR);
        speedLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        
        JSlider speedSlider = new JSlider(0, 100, 0);
        speedSlider.setPreferredSize(new Dimension(80, 20));
        speedSlider.setOpaque(false);
        
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
            if (icon.equals("●")) btn.setForeground(Color.decode("#d98888")); // Red record
            centerPanel.add(btn);
        }

        // RIGHT SECTION: Timecode & Rec Info
        JPanel rightPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 15, 5));
        rightPanel.setOpaque(false);
        
        JLabel timeLabel = new JLabel("00:00:07;10");
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
}
