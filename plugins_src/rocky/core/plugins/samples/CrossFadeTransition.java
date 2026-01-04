package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyTransition;
import java.awt.AlphaComposite;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Sample plugin demonstrating a simple crossfade transition.
 */
public class CrossFadeTransition implements RockyTransition {
    @Override
    public String getName() { return "Fundido Encadenado"; }
    @Override
    public String getDescription() { return "Transición suave entre dos clips."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Fundidos"; }

    @Override
    public List<PluginParameter> getParameters() {
        return new ArrayList<>(); // No parameters needed for standard crossfade
    }

    @Override
    public void render(Graphics2D g2d, int width, int height, BufferedImage clipA, BufferedImage clipB, float progress, Map<String, Object> params) {
        // Progress 0.0 = Only Clip A
        // Progress 1.0 = Only Clip B
        
        // 1. Draw Clip A (Full opacity)
        g2d.drawImage(clipA, 0, 0, width, height, null);
        
        // 2. Draw Clip B (With progress alpha)
        java.awt.Composite old = g2d.getComposite();
        g2d.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, progress));
        g2d.drawImage(clipB, 0, 0, width, height, null);
        g2d.setComposite(old);
    }
}
