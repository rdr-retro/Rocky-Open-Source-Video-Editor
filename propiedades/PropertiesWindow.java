package propiedades;

import javax.swing.*;
import java.awt.*;
import b.timeline.TimelineClip;
import propiedades.timelinekeyframes.TimelinePanel;

/**
 * A window to display and edit properties of a TimelineClip.
 * Currently initialized as a blank window.
 */
public class PropertiesWindow extends JFrame {
    
    public PropertiesWindow(TimelineClip clip) {
        setTitle("Propiedades: " + clip.getName());
        setSize(800, 250);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        
        JPanel mainPanel = new JPanel();
        mainPanel.setBackground(Color.decode("#1e1e1e"));
        mainPanel.setLayout(new BorderLayout());
        
        TimelinePanel tp = new TimelinePanel(clip);
        mainPanel.add(tp, BorderLayout.CENTER);
        
        add(mainPanel);
    }
}
