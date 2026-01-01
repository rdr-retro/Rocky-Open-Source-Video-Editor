package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

public class TrackControlPanel extends JPanel {
    public enum TrackType { VIDEO, AUDIO }
    
    private int height = 60; // Current height
    private final Color BG_COLOR_VIDEO = Color.decode("#607079"); // Muted Blue-Grey
    private final Color BG_COLOR_AUDIO = Color.decode("#606070"); // Slightly darker/purplish for audio
    private final Color STRIP_COLOR_VIDEO = Color.decode("#4a6b8a");
    private final Color STRIP_COLOR_AUDIO = Color.decode("#4a4a6b"); // Darker purple-blue strip
    
    private final Color TEXT_COLOR = Color.WHITE;
    
    private JLabel numLabel;
    private ResizeListener resizeListener;
    private boolean isResizing = false;
    private int startY;
    private int startHeight;
    private TrackType type;

    public TrackType getTrackType() {
        return type;
    }

    public void updateTrackNumber(int newNum) {
        if (numLabel != null) numLabel.setText(String.valueOf(newNum));
    }

    public interface ResizeListener {
        void onHeightChanged();
    }

    public interface MoveTrackListener {
        void onMoveRequested(MouseEvent e);
        void onMoveDragged(MouseEvent e);
        void onMoveReleased(MouseEvent e);
    }
    
    private MoveTrackListener moveListener;

    public void setResizeListener(ResizeListener listener) {
        this.resizeListener = listener;
    }

    public void setMoveListener(MoveTrackListener listener) {
        this.moveListener = listener;
    }

    public TrackControlPanel(TrackType type, int trackNumber) {
        this.type = type;
        setLayout(null); 
        setBackground(type == TrackType.VIDEO ? BG_COLOR_VIDEO : BG_COLOR_AUDIO);
        setPreferredSize(new Dimension(250, height));
        setMinimumSize(new Dimension(250, 40)); 
        setMaximumSize(new Dimension(2500, 500)); 
        
        Color stripColor = (type == TrackType.VIDEO) ? STRIP_COLOR_VIDEO : STRIP_COLOR_AUDIO;
        
        // Left Strip (The "Grab" Area)
        JPanel leftStrip = new JPanel();
        leftStrip.setLayout(null);
        leftStrip.setBackground(stripColor);
        leftStrip.setBounds(0, 0, 24, 2000); 
        leftStrip.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.BLACK));
        leftStrip.setCursor(Cursor.getPredefinedCursor(Cursor.MOVE_CURSOR));
        
        MouseAdapter moveAdapter = new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                if (moveListener != null) moveListener.onMoveRequested(e);
            }
            @Override
            public void mouseDragged(MouseEvent e) {
                if (moveListener != null) moveListener.onMoveDragged(e);
            }
            @Override
            public void mouseReleased(MouseEvent e) {
                if (moveListener != null) moveListener.onMoveReleased(e);
            }
        };
        leftStrip.addMouseListener(moveAdapter);
        leftStrip.addMouseMotionListener(moveAdapter);

        // Menu Icon
        JLabel menuIcon = new JLabel("≡");
        menuIcon.setForeground(Color.WHITE);
        menuIcon.setFont(new Font("SansSerif", Font.BOLD, 14));
        menuIcon.setBounds(0, 2, 24, 15);
        menuIcon.setHorizontalAlignment(SwingConstants.CENTER);
        leftStrip.add(menuIcon);
        
        // Track Number
        numLabel = new JLabel(String.valueOf(trackNumber));
        numLabel.setForeground(Color.WHITE);
        numLabel.setFont(new Font("SansSerif", Font.BOLD, 10));
        numLabel.setBounds(0, 20, 24, 15);
        numLabel.setHorizontalAlignment(SwingConstants.CENTER);
        leftStrip.add(numLabel);
        
        // Track Icon (Generic)
        // Icon logic could go here
        
        add(leftStrip);
        
        // Mute / Solo Buttons (Common)
        RoundButton btnM = new RoundButton("M", Color.decode("#d98888"));
        btnM.setBounds(190, 5, 20, 20);
        add(btnM);
        
        RoundButton btnS = new RoundButton("S", Color.decode("#d9c688"));
        btnS.setBounds(215, 5, 20, 20);
        add(btnS);

        if (type == TrackType.VIDEO) {
            setupVideoControls();
        } else {
            setupAudioControls();
        }
        
        setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, Color.BLACK)); // Bottom border
        
        // Mouse Listeners for Resizing
        MouseAdapter resizeAdapter = new MouseAdapter() {
            @Override
            public void mouseMoved(MouseEvent e) {
                if (e.getY() >= getHeight() - 5) {
                    setCursor(Cursor.getPredefinedCursor(Cursor.S_RESIZE_CURSOR));
                } else {
                    setCursor(Cursor.getDefaultCursor());
                }
            }

            @Override
            public void mousePressed(MouseEvent e) {
                if (e.getY() >= getHeight() - 5) {
                    isResizing = true;
                    startY = e.getYOnScreen();
                    startHeight = getHeight();
                }
            }

            @Override
            public void mouseDragged(MouseEvent e) {
                if (isResizing) {
                    int delta = e.getYOnScreen() - startY;
                    int newHeight = Math.max(40, startHeight + delta);
                    if (newHeight != height) {
                        height = newHeight;
                        setPreferredSize(new Dimension(250, height));
                        revalidate();
                        if (resizeListener != null) resizeListener.onHeightChanged(); 
                    }
                }
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                isResizing = false;
            }
        };
        addMouseListener(resizeAdapter);
        addMouseMotionListener(resizeAdapter);
    }
    
    private void setupVideoControls() {
        // "Nivel:" Label
        JLabel nivelLabel = new JLabel("Nivel:");
        nivelLabel.setForeground(TEXT_COLOR);
        nivelLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        nivelLabel.setBounds(30, 25, 40, 15);
        add(nivelLabel);
        
        // "100,0 %" Label
        JLabel valueLabel = new JLabel("100,0 %");
        valueLabel.setForeground(TEXT_COLOR);
        valueLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        valueLabel.setBounds(70, 25, 60, 15);
        add(valueLabel);
        
        // Slider
        JSlider slider = new JSlider(0, 100, 100);
        slider.setOpaque(false);
        slider.setBounds(130, 20, 100, 20);
        add(slider);
    }
    
    private void setupAudioControls() {
        // "Vol:" Label
        JLabel volLabel = new JLabel("Vol:");
        volLabel.setForeground(TEXT_COLOR);
        volLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        volLabel.setBounds(30, 25, 40, 15);
        add(volLabel);
        
        JLabel dbLabel = new JLabel("0,0 dB");
        dbLabel.setForeground(TEXT_COLOR);
        dbLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        dbLabel.setBounds(60, 25, 50, 15);
        add(dbLabel);
        
        JSlider slider = new JSlider(0, 100, 80);
        slider.setOpaque(false);
        slider.setBounds(110, 20, 80, 20);
        add(slider);
        
        // Pan
        JLabel panLabel = new JLabel("Panoramización:");
        panLabel.setForeground(TEXT_COLOR);
        panLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        panLabel.setBounds(30, 42, 80, 15);
        add(panLabel);
        
        JLabel centerLabel = new JLabel("Centro");
        centerLabel.setForeground(TEXT_COLOR);
        centerLabel.setFont(new Font("SansSerif", Font.PLAIN, 10));
        centerLabel.setBounds(115, 42, 50, 15);
        add(centerLabel);
    }
    
    public TrackControlPanel() {
        this(TrackType.VIDEO, 1); // Default
    }

    // Custom Round Button Helper
    private class RoundButton extends JButton {
        private Color circleColor;
        public RoundButton(String text, Color color) {
            super(text);
            this.circleColor = color;
            setContentAreaFilled(false);
            setFocusPainted(false);
            setBorderPainted(false);
            setForeground(Color.BLACK);
            setFont(new Font("SansSerif", Font.BOLD, 10));
            setMargin(new Insets(0,0,0,0));
        }
        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2d = (Graphics2D) g;
            g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2d.setColor(circleColor);
            g2d.fillOval(0, 0, getWidth()-1, getHeight()-1);
            g2d.setColor(Color.BLACK);
            g2d.drawOval(0, 0, getWidth()-1, getHeight()-1);
            super.paintComponent(g);
        }
    }
}

