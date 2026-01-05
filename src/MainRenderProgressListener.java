import rocky.core.render.RenderEngine;
import javax.swing.JProgressBar;
import javax.swing.JDialog;
import javax.swing.JFrame;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import java.io.File;

public class MainRenderProgressListener implements RenderEngine.RenderProgressListener {
    private final JProgressBar progressBar;
    private final JDialog progressDialog;
    private final File finalFile;
    private final JFrame frame;

    public MainRenderProgressListener(JProgressBar progressBar, JDialog progressDialog, File finalFile, JFrame frame) {
        this.progressBar = progressBar;
        this.progressDialog = progressDialog;
        this.finalFile = finalFile;
        this.frame = frame;
    }

    @Override
    public void onProgress(int percentage) {
        SwingUtilities.invokeLater(() -> progressBar.setValue(percentage));
    }

    @Override
    public void onComplete() {
        SwingUtilities.invokeLater(() -> {
            progressDialog.dispose();
            JOptionPane.showMessageDialog(frame, "Renderizado completado:\n" + finalFile.getName());
        });
    }

    @Override
    public void onError(String message) {
        SwingUtilities.invokeLater(() -> {
            progressDialog.dispose();
            JOptionPane.showMessageDialog(frame, "Error en el renderizado:\n" + message, "Error",
                    JOptionPane.ERROR_MESSAGE);
        });
    }
}
