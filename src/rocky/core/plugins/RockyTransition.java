package rocky.core.plugins;

import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.Map;

/**
 * Interface for video transitions that process two overlapping frames.
 */
public interface RockyTransition extends RockyPlugin {
    /**
     * Renders the transition between two images.
     * @param g2d The graphics context of the frame buffer.
     * @param width Frame width.
     * @param height Frame height.
     * @param clipA The "outgoing" frame.
     * @param clipB The "incoming" frame.
     * @param progress Transition progress (0.0 to 1.0).
     * @param params Map of parameter names and their current values.
     */
    void render(Graphics2D g2d, int width, int height, BufferedImage clipA, BufferedImage clipB, float progress, Map<String, Object> params);
}
