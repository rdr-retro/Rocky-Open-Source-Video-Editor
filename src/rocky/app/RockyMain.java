package rocky.app;

import rocky.ui.toolbar.RockyTopToolbar;
import rocky.ui.viewer.VisualizerPanel;
import rocky.core.audio.MasterSoundPanel;
import rocky.ui.timeline.*;

import rocky.ui.navigation.NavigationPanel;
import rocky.core.media.*;
import rocky.core.engine.FrameServer;
import rocky.core.engine.AudioServer;
import rocky.core.render.RenderEngine;
import rocky.core.render.RenderEngine;
import rocky.core.persistence.ProjectManager;
import rocky.core.model.TimelineModel;
import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.*;
import java.awt.event.*;
import java.io.File;

/**
 * Main entrance of the application located at the root.
 * Assembles all Rocky components.
 * 
 * COMPILE: ./compile.sh
 * RUN: ./run.sh
 */
public class RockyMain {
    private static File currentProjectFile = null;

    private static void updatePlaybackRate(double rate, rocky.ui.timeline.TimelinePanel timeline,
            rocky.ui.timeline.BottomBarPanel bottomBar) {
        timeline.setPlaybackRate(rate);
        bottomBar.setRate(rate);
        if (rate != 0 && !timeline.isPlaying()) {
            timeline.startPlayback();
        } else if (rate == 0 && timeline.isPlaying()) {
            timeline.pausePlayback();
        }
    }

    public static void main(String[] args) {
        // --- PLATFORM AUTO-DETECTION ---
        System.out.println("=================================================");
        System.out.println("  Rocky Open Source Video Editor - Initialization");
        System.out.println("  Platform: " + rocky.core.os.Platform.getOSName());
        System.out.println("  Profile:  " + rocky.core.os.Platform.getOptimizationProfile());
        System.out.println("  Encoder:  " + rocky.core.os.Platform.getHardwareEncoder());
        System.out.println("  Loading native libraries from lib/...");
        System.out.println("=================================================");

        // --- PLUGIN SYSTEM ---
        rocky.core.plugins.PluginManager.getInstance();

        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                e.printStackTrace();
            }

            JFrame frame = new JFrame("Rocky Open Source Video Editor (.rocky Projects)");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setExtendedState(JFrame.MAXIMIZED_BOTH); // Maximize window
            frame.setMinimumSize(new Dimension(1024, 768));
            frame.setBackground(Color.decode("#0f051d"));
            frame.setLayout(new BorderLayout());

            ProjectProperties projectProps = new ProjectProperties();
            MediaPool mediaPool = new MediaPool();
            rocky.core.persistence.HistoryManager history = new rocky.core.persistence.HistoryManager();

            // --- PART B: Timeline Components (from package rocky.ui.timeline) ---
            SidebarPanel sidebar = new SidebarPanel();
            TimelineModel model = new TimelineModel();
            TimelinePanel timeline = new TimelinePanel(model);
            timeline.setMediaPool(mediaPool);
            timeline.setSidebar(sidebar);
            timeline.setHistoryManager(history);
            timeline.setProjectProperties(projectProps);
            TimelineRuler ruler = new TimelineRuler(timeline);

            VisualizerPanel visualizer = new VisualizerPanel();
            FrameServer frameServer = new FrameServer(model, mediaPool, visualizer);
            frameServer.setProperties(projectProps);

            MasterSoundPanel masterSound = new MasterSoundPanel();
            AudioServer audioServer = new AudioServer(model, mediaPool, masterSound);

            sidebar.setOnAddTrack(() -> {
                timeline.setTrackHeights(sidebar.getTrackHeights());
                timeline.setTrackTypes(sidebar.getTrackTypesList());
                history.pushState(timeline, projectProps, mediaPool);
            });
            sidebar.setOnReorderTracks((from, to) -> {
                timeline.reorderTracks(from, to);
                timeline.setTrackTypes(sidebar.getTrackTypesList()); // Sync types after reorder
                history.pushState(timeline, projectProps, mediaPool);
            });
            sidebar.setOnRemoveTrack(index -> {
                timeline.removeTrackData(index);
                timeline.setTrackHeights(sidebar.getTrackHeights()); // Sync heights
                timeline.setTrackTypes(sidebar.getTrackTypesList()); // Sync types
                history.pushState(timeline, projectProps, mediaPool);
            });

            JScrollPane scrollPane = new JScrollPane(timeline);
            scrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
            scrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
            scrollPane.setBorder(null);

            JViewport rowViewport = new JViewport();
            rowViewport.setView(sidebar.getSidebarContent());
            scrollPane.setRowHeader(rowViewport);
            scrollPane.setColumnHeaderView(ruler);
            scrollPane.setCorner(JScrollPane.UPPER_LEFT_CORNER, sidebar.getHeaderPanel());

            JPanel centerContainer = new JPanel(new BorderLayout());
            centerContainer.add(scrollPane, BorderLayout.CENTER);

            JPanel scrollbarPanel = new JPanel(new BorderLayout());
            scrollbarPanel.setBackground(Color.decode("#0f051d"));

            JPanel sidebarSpacer = new JPanel();
            sidebarSpacer.setPreferredSize(new Dimension(350, 0));
            sidebarSpacer.setBackground(Color.decode("#0f051d"));
            scrollbarPanel.add(sidebarSpacer, BorderLayout.WEST);

            JScrollBar hScroll = new JScrollBar(JScrollBar.HORIZONTAL);
            scrollbarPanel.add(hScroll, BorderLayout.CENTER);

            hScroll.addAdjustmentListener(e -> {
                double time = e.getValue() / 1000.0;
                if (Math.abs(timeline.getVisibleStartTime() - time) > 0.05) {
                    timeline.setHorizontalScroll(time);
                    ruler.repaint();
                }
            });
            centerContainer.add(scrollbarPanel, BorderLayout.SOUTH);

            timeline.setTimelineListener(
                    new MainTimelineListener(sidebar, visualizer, frameServer, audioServer, timeline, ruler, hScroll));

            // --- UNDO / REDO KEYBOARD SHORTCUTS ---
            KeyboardFocusManager.getCurrentKeyboardFocusManager().addKeyEventDispatcher(
                    new MainUndoRedoDispatcher(history, timeline, projectProps, mediaPool, sidebar));

            timeline.addComponentListener(new TimelineResizeListener(timeline, hScroll));

            // --- PART A: Top Section (Visualizer & MasterSound) ---
            JPanel topPanel = new JPanel(new BorderLayout());
            topPanel.setBackground(Color.decode("#0f051d"));

            // Navigation Panel (Left Side of Visualizer)
            NavigationPanel navPanel = new NavigationPanel();
            navPanel.setProjectProperties(projectProps, () -> {
                // Refresh everything when a template is clicked
                visualizer.updateProperties(projectProps);
                frameServer.setProperties(projectProps);
                audioServer.setProperties(projectProps);
                frameServer.processFrame(timeline.getPlayheadTime(), true);
                model.getBlueline().setFps(projectProps.getFPS());
                for (rocky.core.media.MediaSource source : mediaPool.getAllSources().values()) {
                    source.setProjectSettings(projectProps.getFPS(), projectProps.getAudioSampleRate());
                }
                timeline.repaint();
                ruler.repaint();
            });
            navPanel.setMinimumSize(new Dimension(200, 0));
            navPanel.setPreferredSize(new Dimension(350, 0));

            // Visualizer (Main center content)
            visualizer.setMinimumSize(new Dimension(300, 0));
            visualizer.setOnPlay(() -> timeline.startPlayback());
            visualizer.setOnPause(() -> timeline.stopPlayback());
            visualizer.setOnStop(() -> {
                timeline.stopPlayback();
                timeline.updatePlayheadFromFrame(0);
            });

            // Master Sound (Attached to the right of visualizer)
            masterSound.setPreferredSize(new Dimension(160, 0));

            // Create a split pane for NavPanel and Visualizer
            JSplitPane topSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, navPanel, visualizer);
            topSplit.setDividerLocation(450);
            topSplit.setDividerSize(5);
            topSplit.setBorder(null);
            topSplit.setOpaque(false);
            topSplit.setBackground(Color.decode("#0f051d"));

            topPanel.add(topSplit, BorderLayout.CENTER);
            topPanel.add(masterSound, BorderLayout.EAST);

            // --- TOP TOOLBAR ---
            RockyTopToolbar toolbar = new RockyTopToolbar();
            toolbar.setOnSave(() -> {
                System.out.println("MainAB: onSave triggered");
                if (currentProjectFile != null) {
                    System.out.println("MainAB: Saving to existing file: " + currentProjectFile.getAbsolutePath());
                    ProjectManager.saveProject(timeline, projectProps, mediaPool, currentProjectFile);
                    JOptionPane.showMessageDialog(frame, "Project saved: " + currentProjectFile.getName());
                    return;
                }

                // Fallback to Save As behavior if no file is set
                JFileChooser chooser = new JFileChooser();
                chooser.setFileFilter(new FileNameExtensionFilter("Rocky Project (.rocky)", "rocky"));
                if (chooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                    System.out.println("MainAB: File selected for save");
                    File f = chooser.getSelectedFile();
                    if (!f.getName().endsWith(".rocky")) {
                        f = new File(f.getAbsolutePath() + ".rocky");
                    }
                    currentProjectFile = f;
                    ProjectManager.saveProject(timeline, projectProps, mediaPool, f);
                    JOptionPane.showMessageDialog(frame, "Project saved successfully!");
                }
            });

            toolbar.setOnOpen(() -> {
                System.out.println("MainAB: onOpen triggered");
                JFileChooser chooser = new JFileChooser();
                chooser.setFileFilter(new FileNameExtensionFilter("Rocky Project (.rocky)", "rocky"));
                if (chooser.showOpenDialog(frame) == JFileChooser.APPROVE_OPTION) {
                    System.out.println("MainAB: File selected for load");
                    File f = chooser.getSelectedFile();
                    currentProjectFile = f;
                    ProjectManager.loadProject(timeline, projectProps, mediaPool, sidebar, f);
                    visualizer.updateProperties(projectProps);
                    history.pushState(timeline, projectProps, mediaPool);
                    frame.setTitle("Rocky Open Source Video Editor - " + f.getName());
                }
            });
            toolbar.setOnSettings(() -> {
                SettingsDialog dialog = new SettingsDialog(frame, projectProps);
                dialog.setVisible(true);
                if (dialog.isApproved()) {
                    double oldFPS = projectProps.getFPS();
                    history.pushState(timeline, projectProps, mediaPool);
                    dialog.applyTo(projectProps);
                    double newFPS = projectProps.getFPS();

                    // --- TIME-PRESERVATION LOGIC ---
                    // If project FPS changed, we MUST rescale the entire timeline
                    // to keep the clips at the same absolute time.
                    if (Math.abs(oldFPS - newFPS) > 0.001) {
                        System.out.println("[RockyMain] Rescaling timeline: " + oldFPS + " -> " + newFPS);
                        timeline.getModel().rescaleToFPS(oldFPS, newFPS);
                    }

                    // Force components to acknowledge new settings
                    visualizer.updateProperties(projectProps);
                    frameServer.setProperties(projectProps);
                    audioServer.setProperties(projectProps);
                    // Blueline FPS is already handled inside timeline.rescaleToFPS if called,
                    // but we do it again here for cases where rescaling wasn't needed but FPS might have changed slightly
                    timeline.getModel().getBlueline().setFps(projectProps.getFPS());

                    // Re-init decoders with new scaling (improves performance for 4K)
                    double scale = projectProps.getPreviewScale();

                    for (rocky.core.media.MediaSource source : mediaPool.getAllSources().values()) {
                        source.reinitDecoder(scale);
                        source.setProjectSettings(projectProps.getFPS(), projectProps.getAudioSampleRate());
                    }
                    frameServer.invalidateCache();

                    frameServer.processFrame(timeline.getPlayheadTime(), true);
                    timeline.repaint();
                    ruler.repaint();
                    if (navPanel != null) navPanel.repaint();
                }
            });
            toolbar.setOnRender(() -> {
                JFileChooser chooser = new JFileChooser();
                chooser.setFileFilter(new FileNameExtensionFilter("Video MP4 (.mp4)", "mp4"));
                if (chooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                    File outputFile = chooser.getSelectedFile();
                    if (!outputFile.getName().toLowerCase().endsWith(".mp4")) {
                        outputFile = new File(outputFile.getAbsolutePath() + ".mp4");
                    }

                    // Setup Progress Dialog
                    JDialog progressDialog = new JDialog(frame, "Renderizando...", true);
                    JProgressBar progressBar = new JProgressBar(0, 100);
                    progressBar.setStringPainted(true);
                    progressDialog.add(progressBar, BorderLayout.CENTER);
                    progressDialog.setSize(300, 70);
                    progressDialog.setLocationRelativeTo(frame);

                    RenderEngine engine = new RenderEngine(frameServer);
                    final File finalFile = outputFile;
                    engine.render(outputFile,
                            new MainRenderProgressListener(progressBar, progressDialog, finalFile, frame));
                    progressDialog.setVisible(true);
                }
            });
            frame.add(toolbar, BorderLayout.NORTH);

            // --- MAIN CONTENT (A + B) ---
            JSplitPane mainSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, topPanel, centerContainer);
            mainSplit.setDividerLocation(500);
            mainSplit.setDividerSize(5);
            mainSplit.setBorder(null);

            frame.add(mainSplit, BorderLayout.CENTER);

            BottomBarPanel bottomBar = new BottomBarPanel();
            frame.add(bottomBar, BorderLayout.SOUTH);

            // Wire Bottom Bar Rate
            bottomBar.setOnRateChange(rate -> {
                timeline.setPlaybackRate(rate);
                if (rate != 0 && !timeline.isPlaying()) {
                    timeline.startPlayback();
                } else if (rate == 0 && timeline.isPlaying()) {
                    timeline.pausePlayback();
                }
            });

            // J-K-L Shortcuts and Global Keyboard Listener
            KeyboardFocusManager.getCurrentKeyboardFocusManager().addKeyEventDispatcher(e -> {
                if (e.getID() == KeyEvent.KEY_PRESSED) {
                    int code = e.getKeyCode();
                    double currentRate = timeline.getPlaybackRate();

                    if (code == KeyEvent.VK_L) {
                        if (currentRate <= 0)
                            currentRate = 1.0;
                        else if (currentRate < 1.0)
                            currentRate = 1.0;
                        else
                            currentRate *= 2.0;

                        if (currentRate > 4.0)
                            currentRate = 4.0; // Limit to slider range
                        updatePlaybackRate(currentRate, timeline, bottomBar);
                        return true;
                    } else if (code == KeyEvent.VK_J) {
                        if (currentRate >= 0)
                            currentRate = -1.0;
                        else if (currentRate > -1.0)
                            currentRate = -1.0;
                        else
                            currentRate *= 2.0;

                        if (currentRate < -4.0)
                            currentRate = -4.0;
                        updatePlaybackRate(currentRate, timeline, bottomBar);
                        return true;
                    } else if (code == KeyEvent.VK_K) {
                        updatePlaybackRate(0.0, timeline, bottomBar);
                        return true;
                    } else if (code == KeyEvent.VK_SPACE) {
                        // Global Spacebar Play/Pause (avoiding text fields)
                        Component focusOwner = KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner();
                        if (!(focusOwner instanceof javax.swing.text.JTextComponent) &&
                                !(focusOwner instanceof javax.swing.JComboBox)) {
                            timeline.togglePlayback();
                            return true;
                        }
                    } else if (code == KeyEvent.VK_Z && (e.isControlDown() || e.isMetaDown())) {
                        if (e.isShiftDown()) {
                            history.redo(timeline, projectProps, mediaPool, sidebar);
                        } else {
                            history.undo(timeline, projectProps, mediaPool, sidebar);
                        }
                        visualizer.updateProperties(projectProps);
                        timeline.repaint();
                        ruler.repaint();
                        return true;
                    } else if (code == KeyEvent.VK_Y && (e.isControlDown() || e.isMetaDown())) {
                        history.redo(timeline, projectProps, mediaPool, sidebar);
                        visualizer.updateProperties(projectProps);
                        timeline.repaint();
                        ruler.repaint();
                        return true;
                    }
                }
                return false;
            });

            // --- KEY BINDINGS ---
            // Removed old SPACE binding to favor global dispatcher

            // Initial Snapshot
            history.pushState(timeline, projectProps, mediaPool);

            frame.setLocationRelativeTo(null);
            frame.setVisible(true);
        });
    }
}
