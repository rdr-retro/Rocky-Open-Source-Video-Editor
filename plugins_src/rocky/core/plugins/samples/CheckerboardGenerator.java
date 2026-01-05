package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyMediaGenerator;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Sample plugin for generating a checkerboard pattern.
 */
public class CheckerboardGenerator implements RockyMediaGenerator {
    @Override
    public String getName() { return "Ajedrez"; }
    @Override
    public String getDescription() { return "Genera un patrón de tablero de ajedrez."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Generadores"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Tamaño Cuadro", PluginParameter.Type.SLIDER, 0.1));
        return params;
    }

    @Override
    public void generate(Graphics2D g2, int width, int height, long frame, Map<String, Object> params) {
        double rawSize = ((Number)params.getOrDefault("Tamaño Cuadro", 0.1)).doubleValue();
        int size = (int)(rawSize * width);
        if (size < 4) size = 4;

        for (int y = 0; y < height; y += size) {
            for (int x = 0; x < width; x += size) {
                if (((x / size) + (y / size)) % 2 == 0) {
                    g2.setColor(Color.DARK_GRAY);
                } else {
                    g2.setColor(Color.BLACK);
                }
                g2.fillRect(x, y, size, size);
            }
        }
    }
}
