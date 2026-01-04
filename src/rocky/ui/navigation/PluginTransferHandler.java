package rocky.ui.navigation;

import rocky.core.plugins.RockyPlugin;
import java.awt.datatransfer.DataFlavor;
import java.awt.datatransfer.Transferable;
import java.awt.datatransfer.UnsupportedFlavorException;
import javax.swing.*;

/**
 * Handles the drag and drop of plugins from the explorer to the timeline.
 */
public class PluginTransferHandler extends TransferHandler {
    public static final DataFlavor PLUGIN_FLAVOR = new DataFlavor(RockyPlugin.class, "RockyPlugin");

    @Override
    public int getSourceActions(JComponent c) {
        return COPY;
    }

    @Override
    protected Transferable createTransferable(JComponent c) {
        if (c instanceof PluginCell) {
            return new PluginTransferable(((PluginCell) c).getPlugin());
        }
        return null;
    }

    public static class PluginTransferable implements Transferable {
        private final RockyPlugin plugin;

        public PluginTransferable(RockyPlugin plugin) {
            this.plugin = plugin;
        }

        @Override
        public DataFlavor[] getTransferDataFlavors() {
            return new DataFlavor[]{PLUGIN_FLAVOR};
        }

        @Override
        public boolean isDataFlavorSupported(DataFlavor flavor) {
            return PLUGIN_FLAVOR.equals(flavor);
        }

        @Override
        public Object getTransferData(DataFlavor flavor) throws UnsupportedFlavorException {
            if (!isDataFlavorSupported(flavor)) throw new UnsupportedFlavorException(flavor);
            return plugin;
        }
    }

    /**
     * Interface for components that can provide a plugin for dragging.
     */
    public interface PluginCell {
        RockyPlugin getPlugin();
    }
}
