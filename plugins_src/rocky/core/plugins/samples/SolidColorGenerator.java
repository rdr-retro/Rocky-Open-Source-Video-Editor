package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyMediaGenerator;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Sample plugin for generating a solid color clip.
 */
public class SolidColorGenerator implements RockyMediaGenerator {
    @Override
    public String getName() { return "Color Sólido"; }
    @Override
    public String getDescription() { return "Genera un plano de color uniforme."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Generadores"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        // In a real app, this would be a COLOR type parameter
        params.add(new PluginParameter("Rojo", PluginParameter.Type.SLIDER, 0.5));
        params.add(new PluginParameter("Verde", PluginParameter.Type.SLIDER, 0.2));
        params.add(new PluginParameter("Azul", PluginParameter.Type.SLIDER, 0.8));
        return params;
    }

    @Override
    public void generate(Graphics2D g2, int width, int height, long frame, Map<String, Object> params) {
        float r = ((Number)params.getOrDefault("Rojo", 0.5)).floatValue();
        float g = ((Number)params.getOrDefault("Verde", 0.2)).floatValue();
        float b = ((Number)params.getOrDefault("Azul", 0.8)).floatValue();
        
        g2.setColor(new Color(r, g, b));
        g2.fillRect(0, 0, width, height);
    }
}
