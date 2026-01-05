package rocky.core.plugins;

import java.util.List;

/**
 * Base interface for all Rocky plugins (Effects and Transitions).
 */
public interface RockyPlugin {
    String getName();
    String getDescription();
    String getAuthor();
    String getVersion();
    String getCategory();
    
    /**
     * List of parameters that Rocky will use to build the UI.
     */
    List<PluginParameter> getParameters();
}
