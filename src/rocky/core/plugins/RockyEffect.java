package rocky.core.plugins;

import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.Map;

/**
 * Interface for video effects that process a single frame.
 */
public interface RockyEffect extends RockyPlugin {
    /**
     * Applies the effect onto the provided image and graphics context.
     * @param image The image to process.
     * @param g2d The graphics context of the frame buffer.
     * @param params Map of parameter names and their current values.
     */
    void apply(BufferedImage image, Graphics2D g2d, Map<String, Object> params);
}
