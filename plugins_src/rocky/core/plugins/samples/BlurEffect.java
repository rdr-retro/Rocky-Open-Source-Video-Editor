package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.awt.image.ConvolveOp;
import java.awt.image.Kernel;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Applies a simple box blur to the video.
 */
public class BlurEffect implements RockyEffect {
    @Override
    public String getName() { return "Desenfocar"; }
    @Override
    public String getDescription() { return "Suaviza la imagen desenfocándola."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Estilo"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Radio", PluginParameter.Type.SLIDER, 0.2)); // 0.0 to 1.0 mapped to kernel size
        return params;
    }

    @Override
    public void apply(BufferedImage image, Graphics2D g2d, Map<String, Object> params) {
        double intensity = (double) params.getOrDefault("Radio", 0.2);
        int radius = (int)(intensity * 10) + 1; // 1 to 11
        if (radius <= 1) return;

        int size = radius * radius;
        float[] data = new float[size];
        float value = 1.0f / size;
        for (int i = 0; i < size; i++) data[i] = value;

        Kernel kernel = new Kernel(radius, radius, data);
        ConvolveOp op = new ConvolveOp(kernel, ConvolveOp.EDGE_NO_OP, null);
        
        BufferedImage blurred = op.filter(image, null);
        
        // Draw back to original graphic context
        g2d.drawImage(blurred, 0, 0, null);
    }
}
