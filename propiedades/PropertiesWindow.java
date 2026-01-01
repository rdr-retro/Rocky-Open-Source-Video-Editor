package propiedades;

import javax.swing.*;
import java.awt.*;
import b.timeline.TimelineClip;

/**
 * A window to display and edit properties of a TimelineClip.
 * Currently initialized as a blank window.
 */
public class PropertiesWindow extends JFrame {
    
    public PropertiesWindow(TimelineClip clip) {
        setTitle("Propiedades: " + clip.getName());
        setSize(400, 300);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        
        JPanel mainPanel = new JPanel();
        mainPanel.setBackground(Color.decode("#1e1e1e"));
        mainPanel.setLayout(new BorderLayout());
        
        JLabel placeholder = new JLabel("Propiedades de: " + clip.getName(), SwingConstants.CENTER);
        placeholder.setForeground(Color.WHITE);
        mainPanel.add(placeholder, BorderLayout.CENTER);
        
        add(mainPanel);
    }
}
