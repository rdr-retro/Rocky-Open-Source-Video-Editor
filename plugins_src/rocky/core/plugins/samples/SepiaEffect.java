package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Applies a Sepia tone to the video.
 */
public class SepiaEffect implements RockyEffect {
    @Override
    public String getName() { return "Sepia"; }
    @Override
    public String getDescription() { return "Aplica un tono sepia antiguo."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Color"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Intensidad", PluginParameter.Type.SLIDER, 1.0));
        return params;
    }

    @Override
    public void apply(BufferedImage image, Graphics2D g2d, Map<String, Object> params) {
        double intensity = (double) params.getOrDefault("Intensidad", 1.0);
        if (intensity <= 0) return;

        int width = image.getWidth();
        int height = image.getHeight();
        int[] pixels = image.getRGB(0, 0, width, height, null, 0, width);

        for (int i = 0; i < pixels.length; i++) {
            int p = pixels[i];
            int r = (p >> 16) & 0xff;
            int g = (p >> 8) & 0xff;
            int b = p & 0xff;

            // Standard Sepia formula
            int tr = (int)(0.393*r + 0.769*g + 0.189*b);
            int tg = (int)(0.349*r + 0.686*g + 0.168*b);
            int tb = (int)(0.272*r + 0.534*g + 0.131*b);

            // Blend with original based on intensity
            r = (int)(r * (1.0 - intensity) + Math.min(255, tr) * intensity);
            g = (int)(g * (1.0 - intensity) + Math.min(255, tg) * intensity);
            b = (int)(b * (1.0 - intensity) + Math.min(255, tb) * intensity);

            pixels[i] = (0xff000000) | (r << 16) | (g << 8) | b;
        }
        
        // This effect modifies the image in-place, which is allowed for RockyEffect if drawing back to the context is not enough
        // However, RockyEffect usually expects us to draw ONTO the g2d or modify the image if it's mutable.
        // Assuming image is mutable from the pipeline. If not, we might need to draw.
        image.setRGB(0, 0, width, height, pixels, 0, width);
    }
}
