package rocky.core.plugins;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Singleton that manages dynamic loading and registry of Rocky plugins.
 */
public class PluginManager {
    private static final PluginManager INSTANCE = new PluginManager();
    
    private final Map<String, RockyEffect> effects = new ConcurrentHashMap<>();
    private final Map<String, RockyTransition> transitions = new ConcurrentHashMap<>();
    private final Map<String, RockyMediaGenerator> generators = new ConcurrentHashMap<>();
    private File pluginsDir;

    private PluginManager() {
        String userHome = System.getProperty("user.home");
        pluginsDir = new File(userHome, ".rocky_plugins");
        if (!pluginsDir.exists()) {
            pluginsDir.mkdirs();
        }
        // Also check local plugins folder
        File localPlugins = new File("plugins");
        if (localPlugins.exists()) {
            scanFolder(localPlugins);
        }
    }

    public static PluginManager getInstance() {
        return INSTANCE;
    }

    public void scanFolder(File folder) {
        File[] jars = folder.listFiles((dir, name) -> name.endsWith(".jar"));
        if (jars == null) return;

        for (File jar : jars) {
            loadPluginsFromJar(jar);
        }
    }

    private void loadPluginsFromJar(File jar) {
        try {
            URL url = jar.toURI().toURL();
            URLClassLoader loader = new URLClassLoader(new URL[]{url}, getClass().getClassLoader());
            
            // Using ServiceLoader for clean discovery
            ServiceLoader<RockyEffect> effectLoader = ServiceLoader.load(RockyEffect.class, loader);
            for (RockyEffect effect : effectLoader) {
                System.out.println("[PluginManager] Loaded Effect: " + effect.getName());
                effects.put(effect.getName(), effect);
            }

            ServiceLoader<RockyTransition> transLoader = ServiceLoader.load(RockyTransition.class, loader);
            for (RockyTransition transition : transLoader) {
                System.out.println("[PluginManager] Loaded Transition: " + transition.getName());
                transitions.put(transition.getName(), transition);
            }

            ServiceLoader<RockyMediaGenerator> genLoader = ServiceLoader.load(RockyMediaGenerator.class, loader);
            for (RockyMediaGenerator gen : genLoader) {
                System.out.println("[PluginManager] Loaded Generator: " + gen.getName());
                generators.put(gen.getName(), gen);
            }

        } catch (Exception e) {
            System.err.println("[PluginManager] Failed to load JAR: " + jar.getName());
            e.printStackTrace();
        }
    }

    public List<RockyEffect> getAvailableEffects() {
        return new ArrayList<>(effects.values());
    }

    public List<RockyTransition> getAvailableTransitions() {
        return new ArrayList<>(transitions.values());
    }

    public List<RockyMediaGenerator> getAvailableGenerators() {
        return new ArrayList<>(generators.values());
    }

    public RockyEffect getEffect(String name) {
        return effects.get(name);
    }

    public RockyTransition getTransition(String name) {
        return transitions.get(name);
    }

    public RockyMediaGenerator getGenerator(String name) {
        return generators.get(name);
    }
}
