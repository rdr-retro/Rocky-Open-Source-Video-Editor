package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyMediaGenerator;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Generator for a solid Yellow color.
 */
public class YellowGenerator implements RockyMediaGenerator {
    @Override
    public String getName() { return "Amarillo"; }
    @Override
    public String getDescription() { return "Genera un plano de color amarillo."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Generadores"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Rojo", PluginParameter.Type.SLIDER, 1.0));
        params.add(new PluginParameter("Verde", PluginParameter.Type.SLIDER, 1.0));
        params.add(new PluginParameter("Azul", PluginParameter.Type.SLIDER, 0.0));
        return params;
    }

    @Override
    public void generate(Graphics2D g2, int width, int height, long frame, Map<String, Object> params) {
        float r = ((Number)params.getOrDefault("Rojo", 1.0)).floatValue();
        float g = ((Number)params.getOrDefault("Verde", 1.0)).floatValue();
        float b = ((Number)params.getOrDefault("Azul", 0.0)).floatValue();
        
        g2.setColor(new Color(r, g, b));
        g2.fillRect(0, 0, width, height);
    }
}
