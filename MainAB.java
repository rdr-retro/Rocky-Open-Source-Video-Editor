import a.visor.VisualizerPanel;
import a.mastersound.MasterSoundPanel;
import b.timeline.*;
import c.toolbar.TopToolbar;
import egine.media.*;
import egine.engine.FrameServer;
import egine.engine.AudioServer;
import egine.render.RenderEngine;
import egine.persistence.ProjectManager;
import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.*;
import java.awt.event.*;
import java.io.File;

/**
 * Main entrance of the application located at the root.
 * Assembles Part A (Visor + MasterSound) and Part B (Timeline).
 * 
 * COMPILE: javac -cp "lib/*:." a/visor/*.java a/mastersound/*.java
 * b/timeline/*.java c/toolbar/*.java egine/media/*.java egine/engine/*.java
 * egine/render/*.java egine/persistence/*.java egine/blueline/*.java
 * MainAB.java
 * RUN: java -cp "lib/*:." MainAB
 */
public class MainAB {
    private static void updatePlaybackRate(double rate, b.timeline.TimelinePanel timeline,
            b.timeline.BottomBarPanel bottomBar) {
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
            frame.setBackground(Color.decode("#1e1e1e"));
            frame.setLayout(new BorderLayout());

            ProjectProperties projectProps = new ProjectProperties();
            MediaPool mediaPool = new MediaPool();
            egine.persistence.HistoryManager history = new egine.persistence.HistoryManager();

            // --- PART B: Timeline Components (from package b.timeline) ---
            SidebarPanel sidebar = new SidebarPanel();
            TimelinePanel timeline = new TimelinePanel();
            timeline.setMediaPool(mediaPool);
            timeline.setSidebar(sidebar);
            timeline.setHistoryManager(history);
            timeline.setProjectProperties(projectProps);
            TimelineRuler ruler = new TimelineRuler(timeline);

            VisualizerPanel visualizer = new VisualizerPanel();
            FrameServer frameServer = new FrameServer(timeline, mediaPool, visualizer);
            frameServer.setProperties(projectProps);

            MasterSoundPanel masterSound = new MasterSoundPanel();
            AudioServer audioServer = new AudioServer(timeline, mediaPool, masterSound);

            sidebar.setOnAddTrack(() -> {
                history.pushState(timeline, projectProps, mediaPool);
                timeline.setTrackHeights(sidebar.getTrackHeights());
            });
            sidebar.setOnReorderTracks((from, to) -> {
                history.pushState(timeline, projectProps, mediaPool);
                timeline.reorderTracks(from, to);
            });
            sidebar.setOnRemoveTrack(index -> {
                history.pushState(timeline, projectProps, mediaPool);
                timeline.removeTrackData(index);
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
            scrollbarPanel.setBackground(Color.decode("#1e1e1e"));

            JPanel sidebarSpacer = new JPanel();
            sidebarSpacer.setPreferredSize(new Dimension(250, 0));
            sidebarSpacer.setBackground(Color.decode("#1e1e1e"));
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
                    frameServer.processFrame(time, force);
                    audioServer.processAudio(frame);
                }

                @Override
                public void onTimelineUpdated() {
                    ruler.repaint();
                    long visibleStart = (long) (timeline.getVisibleStartTime() * 1000);
                    long visibleDuration = (long) (timeline.getVisibleDuration() * 1000);
                    long projectDuration = (long) (timeline.getProjectDuration() * 1000);
                    hScroll.setValues((int) visibleStart, (int) visibleDuration, 0, (int) projectDuration);
                    hScroll.setBlockIncrement((int) visibleDuration);
                    hScroll.setUnitIncrement((int) (visibleDuration / 10));
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
            JPanel topPanel = new JPanel(new GridBagLayout());
            topPanel.setBackground(Color.decode("#1e1e1e"));

            GridBagConstraints gbcTop = new GridBagConstraints();
            gbcTop.fill = GridBagConstraints.BOTH;
            gbcTop.weighty = 1.0;

            // Left Side Placeholder (For future functionality)
            JPanel leftContentPlaceholder = new JPanel();
            leftContentPlaceholder.setBackground(Color.decode("#1e1e1e"));
            leftContentPlaceholder.setPreferredSize(new Dimension(550, 0)); // Even larger as requested
            gbcTop.gridx = 0;
            gbcTop.weightx = 0.0;
            topPanel.add(leftContentPlaceholder, gbcTop);

            // Visualizer (Main center content)
            gbcTop.gridx = 1;
            gbcTop.weightx = 1.0;
            topPanel.add(visualizer, gbcTop);
            visualizer.setOnPlay(() -> timeline.startPlayback());
            visualizer.setOnPause(() -> timeline.stopPlayback());
            visualizer.setOnStop(() -> {
                timeline.stopPlayback();
                timeline.updatePlayheadFromFrame(0);
            });

            // Master Sound (Attached to the right of visualizer)
            gbcTop.gridx = 2;
            gbcTop.weightx = 0.0;
            topPanel.add(masterSound, gbcTop);

            // --- TOP TOOLBAR ---
            TopToolbar toolbar = new TopToolbar();
            toolbar.setOnSave(() -> {
                System.out.println("MainAB: onSave triggered");
                JFileChooser chooser = new JFileChooser();
                chooser.setFileFilter(new FileNameExtensionFilter("Rocky Project (.rocky)", "rocky"));
                if (chooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                    System.out.println("MainAB: File selected for save");
                    File f = chooser.getSelectedFile();
                    if (!f.getName().endsWith(".rocky")) {
                        f = new File(f.getAbsolutePath() + ".rocky");
                    }
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
                    ProjectManager.loadProject(timeline, projectProps, mediaPool, sidebar, chooser.getSelectedFile());
                    visualizer.updateProperties(projectProps);
                    history.pushState(timeline, projectProps, mediaPool);
                }
            });
            toolbar.setOnSettings(() -> {
                JPanel settingsPanel = new JPanel();
                settingsPanel.setLayout(new BoxLayout(settingsPanel, BoxLayout.Y_AXIS));
                settingsPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

                String[] commonRes = {
                        "1920x1080x32; 29,970i",
                        "3840x2160x32; 60p",
                        "1920x1080x32; 60p",
                        "1280x720x32; 29,970p",
                        "720x480x32; 29,970i",
                        "480x270x32; 29,970p",
                        "597x336x32"
                };

                JComboBox<String> projCombo = new JComboBox<>(commonRes);
                projCombo.setEditable(true);
                projCombo.setSelectedItem(projectProps.getProjectRes());

                JComboBox<String> prevCombo = new JComboBox<>(commonRes);
                prevCombo.setEditable(true);
                prevCombo.setSelectedItem(projectProps.getPreviewRes());

                JComboBox<String> dispCombo = new JComboBox<>(commonRes);
                dispCombo.setEditable(true);
                dispCombo.setSelectedItem(projectProps.getDisplayRes());

                JCheckBox lowResCheck = new JCheckBox("Vista Previa de Baja Resolución (Pixelada para mayor fluidez)",
                        projectProps.isLowResPreview());
                lowResCheck.setOpaque(false);
                lowResCheck.setForeground(Color.WHITE);

                autoLayoutSetting(settingsPanel, "Proyecto:", projCombo);
                settingsPanel.add(Box.createVerticalStrut(10));
                autoLayoutSetting(settingsPanel, "Vista Previa:", prevCombo);
                settingsPanel.add(Box.createVerticalStrut(10));
                autoLayoutSetting(settingsPanel, "Visualización:", dispCombo);
                settingsPanel.add(Box.createVerticalStrut(10));
                settingsPanel.add(lowResCheck);

                int result = JOptionPane.showConfirmDialog(frame, settingsPanel, "Ajustes del Proyecto",
                        JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);
                if (result == JOptionPane.OK_OPTION) {
                    history.pushState(timeline, projectProps, mediaPool);
                    projectProps.setProjectRes((String) projCombo.getSelectedItem());
                    projectProps.setPreviewRes((String) prevCombo.getSelectedItem());
                    projectProps.setDisplayRes((String) dispCombo.getSelectedItem());
                    projectProps.setLowResPreview(lowResCheck.isSelected());

                    visualizer.updateProperties(projectProps);
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

                    RenderEngine engine = new RenderEngine(frameServer, 1920, 1080);
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

    private static void autoLayoutSetting(JPanel parent, String label, JComponent comp) {
        JPanel row = new JPanel(new BorderLayout());
        row.setOpaque(false);
        JLabel lbl = new JLabel(label);
        lbl.setPreferredSize(new Dimension(100, 25));
        row.add(lbl, BorderLayout.WEST);
        row.add(comp, BorderLayout.CENTER);
        parent.add(row);
    }
}
