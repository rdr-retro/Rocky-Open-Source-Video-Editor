package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyEffect;
import java.awt.Graphics2D;
import java.awt.color.ColorSpace;
import java.awt.image.BufferedImage;
import java.awt.image.ColorConvertOp;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Sample plugin demonstrating a simple Black and White effect.
 */
public class BlackAndWhiteEffect implements RockyEffect {
    @Override
    public String getName() { return "Blanco y Negro Pro"; }
    @Override
    public String getDescription() { return "Convierte el clip a escala de grises."; }
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

        if (intensity >= 1.0) {
            // Full grayscale
            ColorConvertOp op = new ColorConvertOp(ColorSpace.getInstance(ColorSpace.CS_GRAY), null);
            BufferedImage gray = op.filter(image, null);
            g2d.drawImage(gray, 0, 0, null);
        } else {
            // Blended grayscale
            ColorConvertOp op = new ColorConvertOp(ColorSpace.getInstance(ColorSpace.CS_GRAY), null);
            BufferedImage gray = op.filter(image, null);
            
            java.awt.Composite old = g2d.getComposite();
            g2d.setComposite(java.awt.AlphaComposite.getInstance(java.awt.AlphaComposite.SRC_OVER, (float) intensity));
            g2d.drawImage(gray, 0, 0, null);
            g2d.setComposite(old);
        }
    }
}
