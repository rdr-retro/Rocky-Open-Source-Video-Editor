package rocky.core.plugins;

import java.util.HashMap;
import java.util.Map;

/**
 * Represents an instance of a plugin applied to a clip or transition,
 * containing its specific parameter values.
 */
public class AppliedPlugin {
    private String pluginName;
    private boolean enabled = true;
    private Map<String, Object> parameters = new HashMap<>();
    private transient RockyPlugin pluginInstance; // Not stored in JSON/persistence

    public AppliedPlugin(String pluginName) {
        this.pluginName = pluginName;
    }

    public String getPluginName() { return pluginName; }
    
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    
    public Map<String, Object> getParameters() { return parameters; }
    
    public RockyPlugin getPluginInstance() { return pluginInstance; }
    public void setPluginInstance(RockyPlugin instance) { this.pluginInstance = instance; }

    public void setParameter(String key, Object value) {
        parameters.put(key, value);
    }
}
