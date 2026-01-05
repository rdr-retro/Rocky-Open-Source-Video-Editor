package rocky.ui.properties;

import javax.swing.*;
import java.awt.*;
import rocky.core.model.TimelineClip;
import rocky.core.media.MediaPool;
import rocky.ui.keyframes.KeyframeTimelinePanel;

/**
 * A window to display and edit properties of a TimelineClip.
 */
public class PropertiesWindow extends JFrame {

    public PropertiesWindow(rocky.ui.timeline.TimelinePanel mainTimeline, rocky.ui.timeline.ProjectProperties projectProps,
            TimelineClip clip, MediaPool pool, Runnable onUpdate, rocky.core.persistence.HistoryManager historyManager) {
        setTitle("Panorización/Recorte de evento: " + clip.getName());
        setSize(1000, 700);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);

        PanCropEditor pce = new PanCropEditor(mainTimeline, projectProps, clip, pool, onUpdate, historyManager);
        add(pce);
    }
}
