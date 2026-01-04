import rocky.ui.viewer.VisualizerPanel;
import rocky.core.audio.MasterSoundPanel;
import rocky.ui.timeline.*;
import rocky.ui.toolbar.TopToolbar;
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
public class MainAB {
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
        String os = System.getProperty("os.name");
        String arch = System.getProperty("os.arch");
        System.out.println("=================================================");
        System.out.println("  Rocky Open Source Video Editor - Initialization");
        System.out.println("  OS: " + os);
        System.out.println("  Architecture: " + arch);
        System.out.println("  Loading native libraries from lib/...");
        System.out.println("=================================================");

        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception e) {
                e.printStackTrace();
            }

            JFrame frame = new JFrame("Rocky Open Source Video Editor (.rocky Projects)");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setSize(1200, 800);
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
            sidebarSpacer.setPreferredSize(new Dimension(250, 0));
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

            timeline.setTimelineListener(new TimelinePanel.TimelineListener() {
                @Override
                public void onTimeUpdate(double time, long frame, String timecode, boolean force) {
                    sidebar.setTimecode(timecode);
                    visualizer.setFrameNumber(frame);
                    frameServer.processFrame(time, force);
                    audioServer.processAudio(frame);
                }

                @Override
                public void onTimelineUpdated() {
                    // Invalidate cache to prevent ghost images when clips are moved/deleted
                    frameServer.invalidateCache();
                    frameServer.processFrame(timeline.getPlayheadTime(), true);

                    ruler.repaint();
                    long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
                    long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
                    long projectDuration = (long) (timeline.getProjectDuration() * 1000);
                    hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
                    hScroll.setBlockIncrement((int) visibleDuration);
                    hScroll.setUnitIncrement((int) (visibleDuration / 10));
                }
            });

            // --- UNDO / REDO KEYBOARD SHORTCUTS ---
            KeyboardFocusManager.getCurrentKeyboardFocusManager().addKeyEventDispatcher(new KeyEventDispatcher() {
                @Override
                public boolean dispatchKeyEvent(KeyEvent e) {
                    if (e.getID() == KeyEvent.KEY_PRESSED) {
                        boolean ctrl = (e.getModifiersEx()
                                & (System.getProperty("os.name").contains("Mac") ? KeyEvent.META_DOWN_MASK
                                        : KeyEvent.CTRL_DOWN_MASK)) != 0;
                        if (ctrl) {
                            if (e.getKeyCode() == KeyEvent.VK_Z) {
                                if (e.isShiftDown()) {
                                    history.redo(timeline, projectProps, mediaPool, sidebar);
                                } else {
                                    history.undo(timeline, projectProps, mediaPool, sidebar);
                                }
                                timeline.repaint();
                                return true;
                            } else if (e.getKeyCode() == KeyEvent.VK_Y) {
                                history.redo(timeline, projectProps, mediaPool, sidebar);
                                timeline.repaint();
                                return true;
                            }
                        }
                    }
                    return false;
                }
            });

            timeline.addComponentListener(new ComponentAdapter() {
                @Override
                public void componentResized(ComponentEvent e) {
                    long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
                    long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
                    long projectDuration = (long) (timeline.getProjectDuration() * 1000);
                    hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
                    hScroll.setBlockIncrement((int) visibleDuration);
                    hScroll.setUnitIncrement((int) (visibleDuration / 10));
                }
            });

            // --- PART A: Top Section (Visualizer & MasterSound) ---
            JPanel topPanel = new JPanel(new BorderLayout());
            topPanel.setBackground(Color.decode("#0f051d"));

            // Navigation Panel (Left Side of Visualizer)
            NavigationPanel navPanel = new NavigationPanel();
            navPanel.setProjectProperties(projectProps, () -> {
                // Refresh everything when a template is clicked
                visualizer.updateProperties(projectProps);
                frameServer.setProperties(projectProps);
                frameServer.processFrame(timeline.getPlayheadTime(), true);
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
            topSplit.setDividerLocation(350);
            topSplit.setDividerSize(5);
            topSplit.setBorder(null);
            topSplit.setOpaque(false);
            topSplit.setBackground(Color.decode("#0f051d"));

            topPanel.add(topSplit, BorderLayout.CENTER);
            topPanel.add(masterSound, BorderLayout.EAST);

            // --- TOP TOOLBAR ---
            TopToolbar toolbar = new TopToolbar();
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
                    history.pushState(timeline, projectProps, mediaPool);
                    dialog.applyTo(projectProps);

                    // Force components to acknowledge new settings
                    visualizer.updateProperties(projectProps);
                    frameServer.setProperties(projectProps);

                    // Re-init decoders with new scaling (improves performance for 4K)
                    double scale = projectProps.getPreviewScale();
                    // VEGAS PROXY MODEL: Cap scale at 0.25 (1/4) if Proxy Mode is enabled
                    // Logic removed

                    for (rocky.core.media.MediaSource source : mediaPool.getAllSources().values()) {
                        source.reinitDecoder(scale);
                    }
                    frameServer.invalidateCache();

                    frameServer.processFrame(timeline.getPlayheadTime(), true);
                    timeline.repaint();
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
                    engine.render(outputFile, new RenderEngine.RenderProgressListener() {
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
                    });
                    progressDialog.setVisible(true);
                }
            });
            frame.add(toolbar, BorderLayout.NORTH);

            // --- MAIN CONTENT (A + B) ---
            JSplitPane mainSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, topPanel, centerContainer);
            mainSplit.setDividerLocation(400);
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
