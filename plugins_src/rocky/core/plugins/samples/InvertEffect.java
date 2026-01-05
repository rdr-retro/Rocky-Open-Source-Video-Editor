package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Inverts the colors of the video.
 */
public class InvertEffect implements RockyEffect {
    @Override
    public String getName() { return "Invertir"; }
    @Override
    public String getDescription() { return "Invierte los colores del clip."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Color"; }

    @Override
    public List<PluginParameter> getParameters() {
        return new ArrayList<>(); // Simple on/off effect
    }

    @Override
    public void apply(BufferedImage image, Graphics2D g2d, Map<String, Object> params) {
        int width = image.getWidth();
        int height = image.getHeight();
        int[] pixels = image.getRGB(0, 0, width, height, null, 0, width);

        for (int i = 0; i < pixels.length; i++) {
            int p = pixels[i];
            int a = (p >> 24) & 0xff;
            int r = (p >> 16) & 0xff;
            int g = (p >> 8) & 0xff;
            int b = p & 0xff;

            r = 255 - r;
            g = 255 - g;
            b = 255 - b;

            pixels[i] = (a << 24) | (r << 16) | (g << 8) | b;
        }

        image.setRGB(0, 0, width, height, pixels, 0, width);
    }
}
