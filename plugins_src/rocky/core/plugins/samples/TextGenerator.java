package rocky.core.plugins.samples;

import rocky.core.plugins.PluginParameter;
import rocky.core.plugins.RockyMediaGenerator;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Generador de Texto simple.
 */
public class TextGenerator implements RockyMediaGenerator {
    @Override
    public String getName() { return "Texto Simple"; }
    @Override
    public String getDescription() { return "Genera texto plano con color y posición."; }
    @Override
    public String getAuthor() { return "Rocky Team"; }
    @Override
    public String getVersion() { return "1.0"; }
    @Override
    public String getCategory() { return "Generadores"; }

    @Override
    public List<PluginParameter> getParameters() {
        List<PluginParameter> params = new ArrayList<>();
        params.add(new PluginParameter("Texto", PluginParameter.Type.TEXT, "Tu Texto Aquí"));
        params.add(new PluginParameter("Fuente", PluginParameter.Type.DROPDOWN, "Arial").withOptions(new String[]{"Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma"}));
        params.add(new PluginParameter("Tamaño", PluginParameter.Type.SLIDER, 100.0));
        params.add(new PluginParameter("Posición X", PluginParameter.Type.SLIDER, 0.5));
        params.add(new PluginParameter("Posición Y", PluginParameter.Type.SLIDER, 0.5));
        params.add(new PluginParameter("Rojo", PluginParameter.Type.SLIDER, 1.0));
        params.add(new PluginParameter("Verde", PluginParameter.Type.SLIDER, 1.0));
        params.add(new PluginParameter("Azul", PluginParameter.Type.SLIDER, 1.0));
        return params;
    }

    @Override
    public void generate(Graphics2D g2, int width, int height, long frame, Map<String, Object> params) {
        String texto = (String) params.getOrDefault("Texto", "Tu Texto Aquí");
        String fuente = (String) params.getOrDefault("Fuente", "Arial");
        float size = ((Number)params.getOrDefault("Tamaño", 100.0)).floatValue();
        float xRel = ((Number)params.getOrDefault("Posición X", 0.5)).floatValue();
        float yRel = ((Number)params.getOrDefault("Posición Y", 0.5)).floatValue();
        float r = ((Number)params.getOrDefault("Rojo", 1.0)).floatValue();
        float g = ((Number)params.getOrDefault("Verde", 1.0)).floatValue();
        float b = ((Number)params.getOrDefault("Azul", 1.0)).floatValue();

        // Fondo transparente (ROCKY soporta transparencia en generadores)
        // No dibujamos fondo para permitir superposición si el motor lo soporta.
        // Si se necesita fondo, se puede combinar con un SolidColorGenerator en otra pista.

        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        g2.setColor(new Color(r, g, b));
        g2.setFont(new Font(fuente, Font.BOLD, (int)size));

        java.awt.FontMetrics fm = g2.getFontMetrics();
        int textWidth = fm.stringWidth(texto);
        int textHeight = fm.getAscent();

        int x = (int)(width * xRel) - (textWidth / 2); // Centrado en el punto X
        int y = (int)(height * yRel) + (textHeight / 4); // Centrado aproximado en Y

        g2.drawString(texto, x, y);
    }
}
