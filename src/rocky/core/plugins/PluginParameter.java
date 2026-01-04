package rocky.core.plugins;

import java.util.ArrayList;
import java.util.List;

/**
 * Defines a parameter for a plugin that can be controlled via UI.
 */
public class PluginParameter {
    public enum Type {
        SLIDER, CHECKBOX, COLOR, TEXT, DROPDOWN
    }

    private String name;
    private Type type;
    private Object defaultValue;
    private double min = 0.0;
    private double max = 1.0;
    private String[] options;

    public PluginParameter(String name, Type type, Object defaultValue) {
        this.name = name;
        this.type = type;
        this.defaultValue = defaultValue;
    }

    public PluginParameter withRange(double min, double max) {
        this.min = min;
        this.max = max;
        return this;
    }

    public PluginParameter withOptions(String[] options) {
        this.options = options;
        return this;
    }

    public String getName() { return name; }
    public Type getType() { return type; }
    public Object getDefaultValue() { return defaultValue; }
    public double getMin() { return min; }
    public double getMax() { return max; }
    public String[] getOptions() { return options; }
}
