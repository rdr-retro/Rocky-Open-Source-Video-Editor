package propiedades;

import javax.swing.*;
import java.awt.*;
import b.timeline.TimelineClip;
import egine.media.MediaPool;
import propiedades.timelinekeyframes.TimelinePanel;

/**
 * A window to display and edit properties of a TimelineClip.
 */
public class PropertiesWindow extends JFrame {

    public PropertiesWindow(TimelineClip clip, MediaPool pool, Runnable onUpdate) {
        setTitle("Panorización/Recorte de evento: " + clip.getName());
        setSize(1000, 700);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);

        PanCropEditor pce = new PanCropEditor(clip, pool, onUpdate);
        add(pce);
    }
}
