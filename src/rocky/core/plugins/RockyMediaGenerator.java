package rocky.core.plugins;

import java.awt.Graphics2D;
import java.util.Map;

/**
 * Interface for plugins that generate visual content from scratch.
 * Useful for solid colors, gradients, text, or noise.
 */
public interface RockyMediaGenerator extends RockyPlugin {
    /**
     * Generates a frame.
     * 
     * @param g2 The graphics context to draw on.
     * @param width The target width.
     * @param height The target height.
     * @param frame The clip-local frame index.
     * @param params Current parameter values.
     */
    void generate(Graphics2D g2, int width, int height, long frame, Map<String, Object> params);
}
