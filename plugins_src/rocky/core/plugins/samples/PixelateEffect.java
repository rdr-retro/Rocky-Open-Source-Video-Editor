package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Pixelates the video.
 */
public class PixelateEffect implements RockyEffect {
    @Override
    public String getName() { return "Pixelar"; }
    @Override
    public String getDescription() { return "Pixela la imagen reduciendo la resolución."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Estilo"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Tamaño", PluginParameter.Type.SLIDER, 0.1)); // 0.0 to 1.0
        return params;
    }

    @Override
    public void apply(BufferedImage image, Graphics2D g2d, Map<String, Object> params) {
        double intensity = (double) params.getOrDefault("Tamaño", 0.1);
        int blockSize = (int)(intensity * 50) + 1; // 1 to 51
        if (blockSize <= 1) return;

        int width = image.getWidth();
        int height = image.getHeight();
        
        // Simple heavy pixelation: scale down then scale up
        int w = width / blockSize;
        int h = height / blockSize;
        if (w < 1) w = 1;
        if (h < 1) h = 1;

        BufferedImage temp = new BufferedImage(w, h, image.getType());
        Graphics2D gtemp = temp.createGraphics();
        gtemp.drawImage(image, 0, 0, w, h, null);
        gtemp.dispose();

        g2d.drawImage(temp, 0, 0, width, height, null);
    }
}
