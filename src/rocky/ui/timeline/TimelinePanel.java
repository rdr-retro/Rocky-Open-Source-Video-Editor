package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import rocky.core.media.PeakManager;
import rocky.core.media.MediaSource;
import rocky.ui.properties.PropertiesWindow;

public class TimelinePanel extends JPanel {
    private int mouseX = -1; // Hover cursor position
    private Timer repaintTimer;
    private static TimelineClip copiedClip = null;
    private rocky.core.blueline.Blueline blueline = new rocky.core.blueline.Blueline();
    private final java.util.concurrent.atomic.AtomicLong layoutRevision = new java.util.concurrent.atomic.AtomicLong(0);

    public double getFPS() {
        return (projectProps != null) ? projectProps.getFPS() : 30.0;
    }

    // View State
    private double pixelsPerSecond = 100.0; // Dynamic Zoom Scale
    private double visibleStartTime = 0.0; // Time at X=0 (in seconds)

    // Limits (Sony Vegas style)
    private final double MIN_ZOOM = 0.5; // Comprimid (overview)
    private final double MAX_ZOOM = 5000.0; // Detalle (frame level)

    // Project Settings
    private double projectDuration = 300.0; // Seconds (Default 5 mins)

    // Colors
    private final Color BG_COLOR = Color.decode("#0f051d");
    private final Color HOVER_CURSOR_COLOR = Color.decode("#9d50bb");

    // Media
    private rocky.core.media.MediaPool mediaPool;
    private SidebarPanel sidebar;
    private rocky.core.persistence.HistoryManager historyManager;
    private ProjectProperties projectProps;

    public void setHistoryManager(rocky.core.persistence.HistoryManager historyManager) {
        this.historyManager = historyManager;
        if (historyManager != null && projectProps != null) {
            // Initial snapshot of the current state
            historyManager.pushState(this, projectProps, mediaPool);
        }
    }

    public void setProjectProperties(ProjectProperties props) {
        this.projectProps = props;
    }

    public ProjectProperties getProjectProperties() {
        return projectProps;
    }

    public void setSidebar(SidebarPanel sidebar) {
        this.sidebar = sidebar;
    }

    public TrackControlPanel.TrackType getTrackType(int index) {
        if (sidebar != null)
            return sidebar.getTrackType(index);
        return null;
    }

    // Clips
    private java.util.List<TimelineClip> clips = new java.util.ArrayList<>();

    // --- PUBLIC ACCESSORS FOR RULER ---
    public double getPixelsPerSecond() {
        return pixelsPerSecond;
    }

    public double getVisibleStartTime() {
        return visibleStartTime;
    }

    public long getPlayheadFrame() {
        return blueline.getPlayheadFrame();
    }

    public double getPlayheadTime() {
        return blueline.getPlayheadFrame() / getFPS();
    }

    public java.util.List<TimelineClip> getClips() {
        synchronized (clips) {
            return new java.util.ArrayList<>(clips);
        }
    }

    public java.util.List<Integer> getTrackHeights() {
        return trackHeights;
    }

    public java.util.List<TrackControlPanel.TrackType> getTrackTypes() {
        java.util.List<TrackControlPanel.TrackType> types = new java.util.ArrayList<>();
        if (sidebar != null) {
            for (int i = 0; i < trackHeights.size(); i++) {
                types.add(sidebar.getTrackType(i));
            }
        }
        return types;
    }

    public Color getPlayheadColor() {
        return blueline.getColor();
    }

    public void setMediaPool(rocky.core.media.MediaPool pool) {
        this.mediaPool = pool;
    }

    public void clearClips() {
        synchronized (clips) {
            clips.clear();
        }
        layoutRevision.incrementAndGet();
        fireTimelineUpdated();
    }

    public void addClip(TimelineClip clip) {
        synchronized (clips) {
            clips.add(clip);
        }

        // --- AUTO PROXY ON INSERT ---
        MediaSource source = mediaPool.getSource(clip.getMediaSourceId());
        if (source != null && source.isVideo()) {
            if (source.getProxyFilePath() != null) {
                // Proxy already exists, apply it
                source.setProxyUsed(true);
            } else if (!source.isGeneratingProxy()) {
                // Trigger generation
                source.setGeneratingProxy(true);
                rocky.core.media.ProxyGenerator.generateProxy(new java.io.File(source.getFilePath()),
                        projectProps.getProxyHeight(), projectProps.getProxyBitrate(), (path) -> {
                            javax.swing.SwingUtilities.invokeLater(() -> {
                                source.setupProxy(path);
                                source.setGeneratingProxy(false);
                                source.setProxyUsed(true);
                                repaint();
                                updatePlayheadFromFrame(getPlayheadFrame(), true);
                            });
                        });
            }
        }

        layoutRevision.incrementAndGet();
        fireTimelineUpdated();
    }

    public void removeClip(TimelineClip clip) {
        synchronized (clips) {
            clips.remove(clip);
        }
        layoutRevision.incrementAndGet();
        fireTimelineUpdated();
    }

    // --- ACCESSORS FOR SCROLLBAR ---
    public long getContentDurationFrames() {
        long maxFrame = 0;
        for (TimelineClip clip : clips) {
            long end = clip.getStartFrame() + clip.getDurationFrames();
            if (end > maxFrame)
                maxFrame = end;
        }
        return maxFrame;
    }

    public double getProjectDuration() {
        // Calculate dynamic duration based on content
        double maxTime = 300.0; // Minimum 5 minutes
        for (TimelineClip clip : clips) {
            double end = (clip.getStartFrame() + clip.getDurationFrames()) / (double) getFPS();
            if (end > maxTime)
                maxTime = end;
        }
        // Add some padding at the end (e.g. 1 minute)
        return maxTime + 60.0;
    }

    public double getVisibleDuration() {
        if (pixelsPerSecond <= 0)
            return 0;
        return getWidth() / pixelsPerSecond;
    }

    public double screenToTime(int x) {
        return visibleStartTime + (x / pixelsPerSecond);
    }

    public int timeToScreen(double time) {
        return (int) ((time - visibleStartTime) * pixelsPerSecond);
    }

    public void setPlayheadFromScreenX(int x) {
        updatePlayhead(x);
    }

    public void updatePlayheadFromFrame(long frame) {
        updatePlayheadFromFrame(frame, false);
    }

    public void updatePlayheadFromFrame(long frame, boolean force) {
        blueline.setPlayheadFrame(frame);
        double time = frame / (double) getFPS();

        // Auto-scroll logic: if playing and playhead goes off-screen, jump view
        double newScroll = blueline.calculateAutoScroll(visibleStartTime, getVisibleDuration());
        if (newScroll >= 0) {
            visibleStartTime = newScroll;
        }

        for (TimelineListener listener : listeners) {
            listener.onTimeUpdate(time, frame, blueline.formatTimecode(frame), force);
            listener.onTimelineUpdated();
        }
        repaint();
    }

    public boolean isPlaying() {
        return blueline.isPlaying();
    }

    public void togglePlayback() {
        if (blueline.isPlaying()) {
            pausePlayback();
        } else {
            startPlayback();
        }
    }

    public void startPlayback() {
        blueline.startPlayback();
    }

    public void stopPlayback() {
        long start = blueline.getPlaybackStartFrame();
        blueline.stopPlayback();
        // Restore playhead to start position
        updatePlayheadFromFrame(start);
    }

    public void pausePlayback() {
        blueline.stopPlayback();
        repaint();
    }

    public double getPlaybackRate() {
        return blueline.getPlaybackRate();
    }

    public void setPlaybackRate(double rate) {
        blueline.setPlaybackRate(rate);
    }

    public TimelinePanel() {
        setBackground(BG_COLOR);
        setFocusable(true);

        // Debounce PeakManager repaints (max 30 FPS for UI updates)
        repaintTimer = new Timer(33, e -> repaint());
        repaintTimer.setRepeats(false);
        PeakManager.getInstance().addUpdateListener(() -> {
            if (!repaintTimer.isRunning())
                repaintTimer.start();
        });

        MouseAdapter interactionHandler = new MouseAdapter() {
            private final int RESIZE_MARGIN = 10;
            private TimelineClip activeClip = null;
            private int interactionMode = 0;
            private int dragStartX = 0;
            private int interactionStartY = 0;
            private long originalStart = 0;
            private int originalTrackIndex = 0;
            private long originalDuration = 0;
            private double originalOpacity = 0;
            private double originalStartOpacity = 0;
            private double originalEndOpacity = 0;

            @Override
            public void mouseMoved(MouseEvent e) {
                mouseX = e.getX();
                int mouseY = e.getY();

                boolean cursorSet = false;
                int currentY = 0; // NO RULER OFFSET
                for (int i = 0; i < trackHeights.size(); i++) {
                    int trackH = trackHeights.get(i);
                    for (TimelineClip clip : clips) {
                        if (clip.getTrackIndex() == i) {
                            int clipX = timeToScreen(clip.getStartFrame() / (double) getFPS());
                            int clipW = (int) (clip.getDurationFrames() / (double) getFPS() * pixelsPerSecond);

                            if (mouseY >= currentY && mouseY < currentY + trackH) {
                                int headerH = 20;
                                int bodyTopY = currentY + headerH;

                                // FX / Proxy labels hover
                                if (mouseY < currentY + 20 && e.getX() >= clipX + clipW - 60
                                        && e.getX() <= clipX + clipW) {
                                    setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
                                    cursorSet = true;
                                } else if (Math.abs(e.getX() - clipX) <= RESIZE_MARGIN) {
                                    setCursor(Cursor.getPredefinedCursor(Cursor.W_RESIZE_CURSOR));
                                    cursorSet = true;
                                } else if (Math.abs(e.getX() - (clipX + clipW)) <= RESIZE_MARGIN) {
                                    setCursor(Cursor.getPredefinedCursor(Cursor.E_RESIZE_CURSOR));
                                    cursorSet = true;
                                } else {
                                    int opacityY1 = bodyTopY
                                            + (int) ((1.0 - clip.getStartOpacity()) * (trackH - headerH - 2));
                                    int opacityY2 = bodyTopY
                                            + (int) ((1.0 - clip.getEndOpacity()) * (trackH - headerH - 2));

                                    // Hit detection for handles at TOP EDGE (bodyTopY)
                                    if (Math.abs(mouseY - bodyTopY) <= 10) {
                                        // Fade In / Start Opacity Point
                                        if (e.getX() >= clipX && e.getX() <= clipX + 20) {
                                            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
                                            cursorSet = true;
                                        }
                                        // Fade Out / End Opacity Point
                                        else if (e.getX() >= clipX + clipW - 20 && e.getX() <= clipX + clipW) {
                                            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
                                            cursorSet = true;
                                        }
                                        // Central Opacity Handle (Center of the ramp)
                                        else if (e.getX() > clipX + (clipW / 2) - 15
                                                && e.getX() < clipX + (clipW / 2) + 15) {
                                            setCursor(Cursor.getPredefinedCursor(Cursor.N_RESIZE_CURSOR));
                                            cursorSet = true;
                                        }
                                    }
                                    // Opacity line in general (still detectable by ramp position)
                                    else if (e.getX() > clipX && e.getX() < clipX + clipW) {
                                        double progress = (double) (e.getX() - clipX) / clipW;
                                        int lineY = (int) (opacityY1 + progress * (opacityY2 - opacityY1));
                                        if (Math.abs(mouseY - lineY) <= 8) {
                                            setCursor(Cursor.getPredefinedCursor(Cursor.N_RESIZE_CURSOR));
                                            cursorSet = true;
                                        }
                                    }

                                    if (!cursorSet && e.getX() > clipX && e.getX() < clipX + clipW) {
                                        setCursor(Cursor.getPredefinedCursor(Cursor.MOVE_CURSOR));
                                        cursorSet = true;
                                    }
                                }
                            }
                        }
                    }
                    currentY += trackH;
                }

                if (!cursorSet)
                    setCursor(Cursor.getDefaultCursor());
                repaint();
            }

            @Override
            public void mousePressed(MouseEvent e) {
                int mouseY = e.getY();
                int mouseX = e.getX();

                activeClip = null;

                int currentY = 0;
                for (int i = 0; i < trackHeights.size(); i++) {
                    int trackH = trackHeights.get(i);
                    for (TimelineClip clip : clips) {
                        if (clip.getTrackIndex() == i) {
                            int clipX = timeToScreen(clip.getStartFrame() / (double) getFPS());
                            int clipW = (int) (clip.getDurationFrames() / (double) getFPS() * pixelsPerSecond);

                            int headerH = 20;
                            int bodyTopY = currentY + headerH;

                            if (mouseY >= currentY && mouseY < currentY + trackH) {
                                // REMOVED: Immediate pushState here (we'll push on mouseReleased if something
                                // changed)

                                // Check for labels click
                                if (mouseY < currentY + 20 && mouseX >= clipX + clipW - 60 && mouseX <= clipX + clipW) {
                                    if (mouseX >= clipX + clipW - 30) {
                                        // FX Button
                                        PropertiesWindow pw = new PropertiesWindow(TimelinePanel.this, projectProps,
                                                clip,
                                                mediaPool, () -> {
                                                    updatePlayheadFromFrame(getPlayheadFrame(), true);
                                                }, historyManager);
                                        if (timeListener != null)
                                            timeListener.onTimelineUpdated();
                                        pw.setVisible(true);
                                    } else {
                                        // Proxy (px) Button
                                        MediaSource source = mediaPool.getSource(clip.getMediaSourceId());
                                        if (source != null) {
                                            if (source.getProxyFilePath() != null) {
                                                // Toggle proxy
                                                source.setProxyUsed(!source.isProxyActive());
                                                repaint();
                                                updatePlayheadFromFrame(getPlayheadFrame(), true);
                                            } else if (!source.isGeneratingProxy()) {
                                                source.setGeneratingProxy(true);
                                                rocky.core.media.ProxyGenerator.generateProxy(
                                                        new java.io.File(source.getFilePath()),
                                                        projectProps.getProxyHeight(), projectProps.getProxyBitrate(),
                                                        (path) -> {
                                                            javax.swing.SwingUtilities.invokeLater(() -> {
                                                                source.setupProxy(path);
                                                                source.setGeneratingProxy(false);
                                                                source.setProxyUsed(true);
                                                                repaint();
                                                                updatePlayheadFromFrame(getPlayheadFrame(), true);
                                                            });
                                                        });
                                                repaint();
                                            }
                                        }
                                    }
                                    return;
                                }

                                // Start/End Opacity Handles at TOP EDGE
                                if (Math.abs(mouseY - bodyTopY) <= 12) {
                                    // Fade In / Start Opacity Handle
                                    if (mouseX >= clipX && mouseX <= clipX + 20) {
                                        startInteraction(clip, 7, mouseX); // Mode 7 = START OPACITY
                                        originalStartOpacity = clip.getStartOpacity();
                                        interactionStartY = mouseY;
                                        return;
                                    }
                                    // Fade Out / End Opacity Handle
                                    if (mouseX >= clipX + clipW - 20 && mouseX <= clipX + clipW) {
                                        startInteraction(clip, 8, mouseX); // Mode 8 = END OPACITY
                                        originalEndOpacity = clip.getEndOpacity();
                                        interactionStartY = mouseY;
                                        return;
                                    }
                                    // Central Opacity Handle
                                    if (mouseX > clipX + (clipW / 2) - 15 && mouseX < clipX + (clipW / 2) + 15) {
                                        startInteraction(clip, 6, mouseX); // Mode 6 = GROUP OPACITY
                                        interactionStartY = mouseY;
                                        originalStartOpacity = clip.getStartOpacity();
                                        originalEndOpacity = clip.getEndOpacity();
                                        return;
                                    }
                                }

                                if (Math.abs(mouseX - clipX) <= RESIZE_MARGIN) {
                                    startInteraction(clip, 2, mouseX); // Left-Edge Resize
                                    return;
                                } else if (Math.abs(mouseX - (clipX + clipW)) <= RESIZE_MARGIN) {
                                    startInteraction(clip, 3, mouseX); // Right-Edge Resize
                                    return;
                                } else if (mouseX > clipX && mouseX < clipX + clipW) {
                                    if (SwingUtilities.isLeftMouseButton(e)) {
                                        startInteraction(clip, 1, mouseX);
                                        interactionStartY = mouseY; // Store Y for vertical move
                                        originalTrackIndex = clip.getTrackIndex();
                                        updatePlayhead(mouseX);
                                    }
                                    return;
                                }
                            }
                        }
                    }
                    currentY += trackH;
                }

                if (activeClip == null) {
                    if (SwingUtilities.isLeftMouseButton(e)) {
                        pausePlayback();
                        updatePlayhead(mouseX);
                    }

                    if (e.isPopupTrigger() || SwingUtilities.isRightMouseButton(e)) {
                        showGeneralMenu(e, mouseX, mouseY);
                    }
                }
            }

            private long originalFadeOut = 0;
            private long originalFadeIn = 0;

            private void startInteraction(TimelineClip clip, int mode, int x) {
                activeClip = clip;
                interactionMode = mode;
                dragStartX = x;
                originalStart = clip.getStartFrame();
                originalDuration = clip.getDurationFrames();
                originalFadeOut = clip.getFadeOutFrames();
                originalFadeIn = clip.getFadeInFrames();
                activeTrackHeight = trackHeights.get(clip.getTrackIndex());
            }

            private int activeTrackHeight = 100;

            @Override
            public void mouseDragged(MouseEvent e) {
                if (activeClip != null) {
                    int deltaX = e.getX() - dragStartX;
                    double deltaSecs = deltaX / pixelsPerSecond;
                    long deltaFrames = Math.round(deltaSecs * getFPS());

                    if (interactionMode == 1) {
                        long newStart = originalStart + deltaFrames;
                        long snappedStart = findSnapFrame(newStart, activeClip);
                        long snappedEnd = findSnapFrame(newStart + originalDuration, activeClip);

                        if (snappedStart != -1 && snappedEnd != -1) {
                            // Both snap, pick the closer one
                            long deltaStart = Math.abs(snappedStart - newStart);
                            long deltaEnd = Math.abs(snappedEnd - (newStart + originalDuration));
                            if (deltaStart <= deltaEnd) {
                                activeClip.setStartFrame(Math.max(0, snappedStart));
                            } else {
                                activeClip.setStartFrame(Math.max(0, snappedEnd - originalDuration));
                            }
                        } else if (snappedStart != -1) {
                            activeClip.setStartFrame(Math.max(0, snappedStart));
                        } else if (snappedEnd != -1) {
                            activeClip.setStartFrame(Math.max(0, snappedEnd - originalDuration));
                        } else {
                            activeClip.setStartFrame(Math.max(0, newStart));
                        }

                        // Vertical Move (Track Switch)
                        int currentMouseY = e.getY();
                        int trackSum = 0;
                        for (int i = 0; i < trackHeights.size(); i++) {
                            int h = trackHeights.get(i);
                            if (currentMouseY >= trackSum && currentMouseY < trackSum + h) {
                                // Check if track type matches
                                TrackControlPanel.TrackType newTrackType = sidebar.getTrackType(i);
                                TrackControlPanel.TrackType oldTrackType = sidebar
                                        .getTrackType(activeClip.getTrackIndex());
                                if (newTrackType == oldTrackType) {
                                    activeClip.setTrackIndex(i);
                                }
                                break;
                            }
                            trackSum += h;
                        }

                        fireTimelineUpdated();
                    } else if (interactionMode == 2) {
                        long newStart = originalStart + deltaFrames;
                        long snappedStart = findSnapFrame(newStart, activeClip);
                        long finalStart = Math.max(0, snappedStart != -1 ? snappedStart : newStart);

                        long endFrame = originalStart + originalDuration;
                        if (finalStart < endFrame - 5) {
                            activeClip.setStartFrame(finalStart);
                            activeClip.setDurationFrames(endFrame - finalStart);
                        }
                        fireTimelineUpdated();
                    } else if (interactionMode == 6) {
                        // Group Opacity Adjustment
                        int deltaY = -(e.getY() - interactionStartY);
                        double deltaOpacity = deltaY / (double) (activeTrackHeight - 20); // 20 is header
                        activeClip.setStartOpacity(originalStartOpacity + deltaOpacity);
                        activeClip.setEndOpacity(originalEndOpacity + deltaOpacity);
                        fireTimelineUpdated();
                    } else if (interactionMode == 7) {
                        // Start Opacity Adjustment (Vertical)
                        int deltaY = e.getY() - interactionStartY;
                        double deltaOp = -deltaY / (double) (activeTrackHeight - 20);
                        activeClip.setStartOpacity(originalStartOpacity + deltaOp);

                        // Fade In Adjustment (Horizontal)
                        long newFade = originalFadeIn + deltaFrames;
                        if (newFade < 0)
                            newFade = 0;
                        if (newFade > activeClip.getDurationFrames() - activeClip.getFadeOutFrames())
                            newFade = activeClip.getDurationFrames() - activeClip.getFadeOutFrames();
                        activeClip.setFadeInFrames(newFade);

                        fireTimelineUpdated();
                    } else if (interactionMode == 8) {
                        // End Opacity Adjustment (Vertical)
                        int deltaY = e.getY() - interactionStartY;
                        double deltaOp = -deltaY / (double) (activeTrackHeight - 20);
                        activeClip.setEndOpacity(originalEndOpacity + deltaOp);

                        // Fade Out Adjustment (Horizontal)
                        long newFade = originalFadeOut - deltaFrames;
                        if (newFade < 0)
                            newFade = 0;
                        if (newFade > activeClip.getDurationFrames() - activeClip.getFadeInFrames())
                            newFade = activeClip.getDurationFrames() - activeClip.getFadeInFrames();
                        activeClip.setFadeOutFrames(newFade);

                        fireTimelineUpdated();
                    } else if (interactionMode == 3) {
                        // Right-Edge Resize (End Trim)
                        long newEnd = originalStart + originalDuration + deltaFrames;
                        long snappedEnd = findSnapFrame(newEnd, activeClip);
                        long finalEnd = snappedEnd != -1 ? snappedEnd : newEnd;

                        long newDuration = Math.max(5, finalEnd - originalStart);
                        activeClip.setDurationFrames(newDuration);
                        fireTimelineUpdated();
                    }

                    repaint();
                } else {
                    if (SwingUtilities.isLeftMouseButton(e)) {
                        mouseX = e.getX();
                        updatePlayhead(mouseX);
                    }
                }
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                if (e.isPopupTrigger() || SwingUtilities.isRightMouseButton(e)) {
                    handleCallback(e);
                } else {
                    if (activeClip != null && interactionMode != 0) {
                        // Action finished (move, resize, or opacity). Push the NEW state.
                        if (historyManager != null) {
                            historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                        }
                    }
                    activeClip = null;
                    interactionMode = 0;
                }
            }

            private void handleCallback(MouseEvent e) {
                int mouseX = e.getX();
                int mouseY = e.getY();
                int currentY = 0;

                for (int i = 0; i < trackHeights.size(); i++) {
                    int trackH = trackHeights.get(i);
                    for (TimelineClip clip : clips) {
                        if (clip.getTrackIndex() == i) {
                            int clipX = timeToScreen(clip.getStartFrame() / (double) getFPS());
                            int clipW = (int) (clip.getDurationFrames() / (double) getFPS() * pixelsPerSecond);

                            int headerH = 20;
                            int bodyTopY = currentY + headerH;

                            if (mouseY >= currentY && mouseY < currentY + trackH) {
                                if (mouseX >= clipX && mouseX <= clipX + clipW) {
                                    // Check if click is in Fade In Area
                                    int fadeInW = (int) (clip.getFadeInFrames() / (double) getFPS() * pixelsPerSecond);
                                    if (fadeInW > 5 && mouseX >= clipX && mouseX <= clipX + fadeInW
                                            && mouseY >= bodyTopY) {
                                        showFadeMenu(e, clip, true);
                                        return;
                                    }

                                    // Check Fade Out Area
                                    int fadeOutW = (int) (clip.getFadeOutFrames() / (double) getFPS()
                                            * pixelsPerSecond);
                                    if (fadeOutW > 5 && mouseX >= clipX + clipW - fadeOutW && mouseX <= clipX + clipW
                                            && mouseY >= bodyTopY) {
                                        showFadeMenu(e, clip, false);
                                        return;
                                    }

                                    // If not in fade area but within clip, show general clip menu
                                    showClipMenu(e, clip);
                                    return;
                                }
                            }
                        }
                    }
                    currentY += trackH;
                }
            }

            private void showClipMenu(MouseEvent e, TimelineClip clip) {
                JPopupMenu menu = new JPopupMenu();

                JMenuItem deleteItem = new JMenuItem("Eliminar");
                deleteItem.addActionListener(ev -> {
                    removeClip(clip);
                    if (historyManager != null) {
                        historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                    }
                    if (timeListener != null)
                        timeListener.onTimelineUpdated();
                });
                menu.add(deleteItem);

                JMenuItem propsItem = new JMenuItem("Propiedades");
                propsItem.addActionListener(ev -> {
                    PropertiesWindow pw = new PropertiesWindow(TimelinePanel.this, projectProps, clip, mediaPool,
                            () -> {
                                updatePlayheadFromFrame(getPlayheadFrame(), true);
                            }, historyManager);
                    pw.setVisible(true);
                });
                menu.add(propsItem);

                menu.addSeparator();

                long phFrame = blueline.getPlayheadFrame();
                boolean canSplit = phFrame > clip.getStartFrame()
                        && phFrame < (clip.getStartFrame() + clip.getDurationFrames());
                JMenuItem splitItem = new JMenuItem("Dividir");
                splitItem.setEnabled(canSplit);
                splitItem.addActionListener(ev -> {
                    splitClipAt(clip, phFrame);
                });
                menu.add(splitItem);

                JMenuItem copyItem = new JMenuItem("Copiar");
                copyItem.addActionListener(ev -> {
                    copiedClip = clip.copy();
                });
                menu.add(copyItem);

                menu.show(e.getComponent(), e.getX(), e.getY());
            }

            private void splitClipAt(TimelineClip clip, long phFrame) {
                if (historyManager != null) {
                    historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                }

                long splitOffset = phFrame - clip.getStartFrame();

                // 1. Create right part
                TimelineClip rightPart = clip.copy();
                rightPart.setStartFrame(phFrame);
                rightPart.setDurationFrames(clip.getDurationFrames() - splitOffset);
                rightPart.setSourceOffsetFrames(rightPart.getSourceOffsetFrames() + splitOffset);

                // Adjust/Remove fades for split point
                clip.setFadeOutFrames(0);
                rightPart.setFadeInFrames(0);

                // Adjust keyframes for right part
                synchronized (rightPart.getTimeKeyframes()) {
                    java.util.Iterator<rocky.ui.keyframes.TimelineKeyframe> it = rightPart.getTimeKeyframes()
                            .iterator();
                    while (it.hasNext()) {
                        rocky.ui.keyframes.TimelineKeyframe k = it.next();
                        if (k.getClipFrame() < splitOffset) {
                            it.remove();
                        } else {
                            k.setClipFrame(k.getClipFrame() - splitOffset);
                        }
                    }
                }

                // 2. Adjust left part (original clip)
                clip.setDurationFrames(splitOffset);
                synchronized (clip.getTimeKeyframes()) {
                    java.util.Iterator<rocky.ui.keyframes.TimelineKeyframe> it = clip.getTimeKeyframes().iterator();
                    while (it.hasNext()) {
                        rocky.ui.keyframes.TimelineKeyframe k = it.next();
                        if (k.getClipFrame() > splitOffset) {
                            it.remove();
                        }
                    }
                }

                synchronized (clips) {
                    clips.add(rightPart);
                }

                if (historyManager != null) {
                    historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                }
                fireTimelineUpdated();
            }

            private void showGeneralMenu(MouseEvent e, int x, int y) {
                JPopupMenu menu = new JPopupMenu();

                JMenuItem pasteItem = new JMenuItem("Pegar");
                pasteItem.setEnabled(copiedClip != null);
                pasteItem.addActionListener(ev -> {
                    if (copiedClip != null) {
                        TimelineClip newClip = copiedClip.copy();

                        // Find track under Y
                        int currentY = 0;
                        int trackIndex = 0;
                        for (int i = 0; i < trackHeights.size(); i++) {
                            int h = trackHeights.get(i);
                            if (y >= currentY && y < currentY + h) {
                                trackIndex = i;
                                break;
                            }
                            currentY += h;
                        }

                        newClip.setTrackIndex(trackIndex);
                        newClip.setStartFrame(Math.round(screenToTime(x) * getFPS()));

                        addClip(newClip);
                        if (historyManager != null) {
                            historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                        }
                    }
                });
                menu.add(pasteItem);

                menu.show(e.getComponent(), x, y);
            }

            private void showFadeMenu(MouseEvent e, TimelineClip clip, boolean isFadeIn) {
                JPopupMenu menu = new JPopupMenu();
                String title = isFadeIn ? "Fade In Type" : "Fade Out Type";
                JLabel label = new JLabel(title);
                label.setBorder(BorderFactory.createEmptyBorder(5, 10, 5, 10));
                label.setFont(label.getFont().deriveFont(Font.BOLD));
                menu.add(label);
                menu.addSeparator();

                ButtonGroup group = new ButtonGroup();
                TimelineClip.FadeType currentType = isFadeIn ? clip.getFadeInType() : clip.getFadeOutType();

                for (TimelineClip.FadeType type : TimelineClip.FadeType.values()) {
                    JRadioButtonMenuItem item = new JRadioButtonMenuItem(
                            type.toString().charAt(0) + type.toString().substring(1).toLowerCase());
                    if (type == currentType)
                        item.setSelected(true);
                    item.addActionListener(ev -> {
                        if (isFadeIn)
                            clip.setFadeInType(type);
                        else
                            clip.setFadeOutType(type);

                        if (historyManager != null) {
                            historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                        }
                        repaint();
                    });
                    group.add(item);
                    menu.add(item);
                }
                menu.show(e.getComponent(), e.getX(), e.getY());
            }

            @Override
            public void mouseExited(MouseEvent e) {
                mouseX = -1;
                repaint();
            }
        };

        addMouseListener(interactionHandler);
        addMouseMotionListener(interactionHandler);

        // Keyboard Shortcuts (Sony Vegas: + / - zoom)
        addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                double zoomFactor = 1.25;
                double mouseTime = (mouseX >= 0) ? screenToTime(mouseX) : screenToTime(getWidth() / 2);

                if (e.getKeyChar() == '+' || e.getKeyCode() == KeyEvent.VK_PLUS || e.getKeyCode() == KeyEvent.VK_ADD) {
                    zoomIn(mouseTime, zoomFactor);
                } else if (e.getKeyChar() == '-' || e.getKeyCode() == KeyEvent.VK_MINUS
                        || e.getKeyCode() == KeyEvent.VK_SUBTRACT) {
                    zoomOut(mouseTime, zoomFactor);
                }
            }
        });

        // ZOOM / PAN - Simplified (Only Zoom)
        addMouseWheelListener(e -> {
            boolean isCtrl = e.isControlDown() || e.isMetaDown();
            double mouseTime = screenToTime(e.getX());

            if (isCtrl) {
                double zoomFactor = 1.1;
                if (e.getPreciseWheelRotation() > 0)
                    zoomOut(mouseTime, zoomFactor);
                else
                    zoomIn(mouseTime, zoomFactor);
            } else {
                // If not locked in JScrollPane, this handles pan. But JScrollPane should handle
                // Pan?
                // Let's allow Wheel pan to update visibility, but we need to notify
                // scrollbar...
                // Ideally, horizontal wheel scrolling should be handled by JScrollPane
                // But for "Vegas" feel of simple vertical wheel = horizontal pan:

                double scrollAmount = (getWidth() / pixelsPerSecond) * 0.1 * e.getPreciseWheelRotation();
                visibleStartTime += scrollAmount;
                if (visibleStartTime < 0)
                    visibleStartTime = 0;

                fireTimelineUpdated();
            }
        });

        // Drop Traget
        setDropTarget(new java.awt.dnd.DropTarget(this, new java.awt.dnd.DropTargetListener() {
            public void dragEnter(java.awt.dnd.DropTargetDragEvent dtde) {
            }

            public void dragOver(java.awt.dnd.DropTargetDragEvent dtde) {
            }

            public void dropActionChanged(java.awt.dnd.DropTargetDragEvent dtde) {
            }

            public void dragExit(java.awt.dnd.DropTargetEvent dte) {
            }

            @Override
            public void drop(java.awt.dnd.DropTargetDropEvent dtde) {
                try {
                    dtde.acceptDrop(java.awt.dnd.DnDConstants.ACTION_COPY);
                    java.util.List<java.io.File> droppedFiles = (java.util.List<java.io.File>) dtde.getTransferable()
                            .getTransferData(java.awt.datatransfer.DataFlavor.javaFileListFlavor);

                    if (droppedFiles != null && !droppedFiles.isEmpty()) {
                        java.io.File file = droppedFiles.get(0);
                        String name = file.getName();

                        Point loc = dtde.getLocation();
                        double droppedTime = screenToTime(loc.x);
                        long startFrame = Math.round(droppedTime * getFPS());

                        int currentY = 0;
                        int targetTrackIndex = -1;
                        for (int i = 0; i < trackHeights.size(); i++) {
                            int h = trackHeights.get(i);
                            if (loc.y >= currentY && loc.y < currentY + h) {
                                targetTrackIndex = i;
                                break;
                            }
                            currentY += h;
                        }

                        // If dropping into an empty timeline or empty area below tracks, create a NEW
                        // track based on media type
                        if (targetTrackIndex == -1 && sidebar != null) {
                            String lower = name.toLowerCase();
                            boolean isAudioFile = lower.endsWith(".mp3") || lower.endsWith(".wav") ||
                                    lower.endsWith(".aac") || lower.endsWith(".m4a") ||
                                    lower.endsWith(".ogg") || lower.endsWith(".flac") ||
                                    lower.endsWith(".caf");

                            TrackControlPanel.TrackType autoType = isAudioFile ? TrackControlPanel.TrackType.AUDIO
                                    : TrackControlPanel.TrackType.VIDEO;

                            sidebar.addTrack(autoType);
                            targetTrackIndex = sidebar.getTrackCount() - 1;
                        }

                        if (targetTrackIndex != -1) {
                            if (historyManager != null) {
                                historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                            }
                            String mediaId = name;
                            if (mediaPool != null) {
                                rocky.core.media.MediaSource source = mediaPool.getSource(mediaId);
                                if (source == null) {
                                    source = new rocky.core.media.MediaSource(mediaId, file.getAbsolutePath(),
                                            projectProps.getPreviewScale());
                                    mediaPool.addSource(source);
                                }

                                long duration = (source.getTotalFrames() > 0) ? source.getTotalFrames()
                                        : Math.round(5 * getFPS()); // Images
                                // default
                                // 5s
                                TrackControlPanel.TrackType trackType = (sidebar != null)
                                        ? sidebar.getTrackType(targetTrackIndex)
                                        : null;

                                boolean isMediaVideo = source.isVideo() || (!source.isVideo() && !source.isAudio());
                                boolean isMediaAudio = source.isAudio();

                                // Rule 1: No audio in video track
                                if (isMediaAudio && trackType == TrackControlPanel.TrackType.VIDEO) {
                                    dtde.dropComplete(false);
                                    return;
                                }
                                // Rule 2: No video/image in audio track
                                if (isMediaVideo && trackType == TrackControlPanel.TrackType.AUDIO) {
                                    dtde.dropComplete(false);
                                    return;
                                }

                                // Calculate Snap for Drop
                                long snappedStart = findSnapFrame(startFrame, null);
                                long snappedEnd = findSnapFrame(startFrame + duration, null);
                                if (snappedStart != -1 && snappedEnd != -1) {
                                    long deltaStart = Math.abs(snappedStart - startFrame);
                                    long deltaEnd = Math.abs(snappedEnd - (startFrame + duration));
                                    if (deltaStart <= deltaEnd)
                                        startFrame = snappedStart;
                                    else
                                        startFrame = snappedEnd - duration;
                                } else if (snappedStart != -1) {
                                    startFrame = snappedStart;
                                } else if (snappedEnd != -1) {
                                    startFrame = snappedEnd - duration;
                                }
                                if (startFrame < 0)
                                    startFrame = 0;

                                TimelineClip clip = new TimelineClip(name, startFrame, duration, targetTrackIndex);
                                clip.setMediaSourceId(mediaId);
                                addClip(clip);

                                // Rule 3: MP4/Video with audio -> Auto create audio track below
                                // We check source.hasAudio() which now uses the more reliable AudioDecoder
                                // probe
                                boolean hasAudio = source.hasAudio();
                                System.out.println("[Drop] Processing " + name + " (Video: " + source.isVideo()
                                        + ", Audio: " + hasAudio + ")");

                                if (source.isVideo() && hasAudio && trackType == TrackControlPanel.TrackType.VIDEO) {
                                    if (sidebar != null) {
                                        int audioTrackIdx = targetTrackIndex + 1;
                                        System.out.println("[Drop] Auto-creating audio track for " + name
                                                + " at index: " + audioTrackIdx);

                                        // 1. Shift existing clips in TimelinePanel
                                        onTrackInserted(audioTrackIdx);
                                        // 2. Insert the track in SidebarPanel
                                        sidebar.addTrack(TrackControlPanel.TrackType.AUDIO, audioTrackIdx);

                                        TimelineClip audioClip = new TimelineClip(name + " (Audio)", startFrame,
                                                duration, audioTrackIdx);
                                        audioClip.setMediaSourceId(mediaId);
                                        addClip(audioClip);
                                    }
                                }
                            }
                            if (historyManager != null) {
                                historyManager.pushState(TimelinePanel.this, projectProps, mediaPool);
                            }
                            repaint();
                        }
                    }
                    dtde.dropComplete(true);
                } catch (Exception ex) {
                    ex.printStackTrace();
                    dtde.dropComplete(false);
                }
            }
        }));
    }

    private void updatePlayhead(int x) {
        pausePlayback();
        double time = screenToTime(x);
        long frame = Math.round(time * getFPS());
        if (frame < 0)
            frame = 0;
        blueline.setPlayheadFrame(frame);
        fireTimelineUpdated();
    }

    private java.util.List<Integer> trackHeights = new java.util.ArrayList<>();

    public void setTrackHeights(java.util.List<Integer> heights) {
        this.trackHeights = heights;
        int totalH = 0;
        for (int h : heights)
            totalH += h;

        // Ensure minimum height to fill Viewport (approximation)
        // or at least allow clicking in empty space
        int minHeight = 800; // Enough for full screen vertical
        if (getParent() instanceof JViewport) {
            minHeight = Math.max(minHeight, getParent().getHeight());
        }

        setPreferredSize(new Dimension(getWidth(), Math.max(minHeight, totalH)));
        revalidate();
        repaint();
    }

    /**
     * Reorders clips when tracks are moved in the sidebar.
     */
    public void reorderTracks(int fromIndex, int toIndex) {
        synchronized (clips) {
            for (TimelineClip clip : clips) {
                int oldIdx = clip.getTrackIndex();
                if (oldIdx == fromIndex) {
                    clip.setTrackIndex(toIndex);
                } else if (fromIndex < toIndex) {
                    // Moving down: Tracks between from and to move up
                    if (oldIdx > fromIndex && oldIdx <= toIndex) {
                        clip.setTrackIndex(oldIdx - 1);
                    }
                } else if (fromIndex > toIndex) {
                    // Moving up: Tracks between to and from move down
                    if (oldIdx >= toIndex && oldIdx < fromIndex) {
                        clip.setTrackIndex(oldIdx + 1);
                    }
                }
            }
        }
        fireTimelineUpdated();
    }

    /**
     * Shifts clips down when a new track is inserted in the middle.
     */
    public void onTrackInserted(int index) {
        synchronized (clips) {
            for (TimelineClip clip : clips) {
                if (clip.getTrackIndex() >= index) {
                    clip.setTrackIndex(clip.getTrackIndex() + 1);
                }
            }
        }
        fireTimelineUpdated();
    }

    /**
     * Removes clips and shifts them up when a track is deleted.
     */
    public void removeTrackData(int index) {
        synchronized (clips) {
            java.util.List<TimelineClip> toRemove = new java.util.ArrayList<>();
            for (TimelineClip clip : clips) {
                if (clip.getTrackIndex() == index) {
                    toRemove.add(clip);
                } else if (clip.getTrackIndex() > index) {
                    clip.setTrackIndex(clip.getTrackIndex() - 1);
                }
            }
            clips.removeAll(toRemove);
        }
        fireTimelineUpdated();
    }

    private long findSnapFrame(long targetFrame, TimelineClip excludeClip) {
        // Dynamic Threshold: proportional to screen distance (e.g. 12 pixels)
        double pixelThreshold = 12.0;
        double thresholdFrames = (pixelThreshold / pixelsPerSecond) * getFPS();

        long closestSnap = -1;
        double minDelta = thresholdFrames + 0.0001; // Tiny margin

        // Candidate 1: Start 0
        double delta0 = Math.abs((double) targetFrame - 0);
        if (delta0 < minDelta) {
            minDelta = delta0;
            closestSnap = 0;
        }

        // Candidate 2: Playhead
        long ph = blueline.getPlayheadFrame();
        double deltaPH = Math.abs((double) targetFrame - ph);
        if (deltaPH < minDelta) {
            minDelta = deltaPH;
            closestSnap = ph;
        }

        // Candidates: Other clip boundaries
        synchronized (clips) {
            for (TimelineClip clip : clips) {
                if (clip == excludeClip)
                    continue;

                // Other clip's start
                long s = clip.getStartFrame();
                double ds = Math.abs((double) targetFrame - s);
                if (ds < minDelta) {
                    minDelta = ds;
                    closestSnap = s;
                }

                // Other clip's end
                long endIdx = clip.getStartFrame() + clip.getDurationFrames();
                double de = Math.abs((double) targetFrame - endIdx);
                if (de < minDelta) {
                    minDelta = de;
                    closestSnap = endIdx;
                }
            }
        }

        return (minDelta <= thresholdFrames) ? closestSnap : -1;
    }

    public interface TimelineListener {
        void onTimeUpdate(double timeInSeconds, long totalFrames, String timecode, boolean force);

        void onTimelineUpdated(); // For syncing ruler/scrollbar
    }

    private final java.util.List<TimelineListener> listeners = new java.util.concurrent.CopyOnWriteArrayList<>();
    private TimelineListener timeListener; // Keep for backward compatibility if needed, but we'll migrate

    public void addTimelineListener(TimelineListener listener) {
        listeners.add(listener);
    }

    public void setTimelineListener(TimelineListener listener) {
        // Migration: Add to list
        listeners.add(listener);
        this.timeListener = listener;
    }

    public String formatTimecode(long totalFrames) {
        return blueline.formatTimecode(totalFrames);
    }

    // External Scroll Control
    public void setHorizontalScroll(double time) {
        this.visibleStartTime = time;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2d = (Graphics2D) g;
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int width = getWidth();
        int height = getHeight();

        // Tracks BG
        int currentY = 0;
        java.util.List<Integer> trackYPositions = new java.util.ArrayList<>();

        double viewStartSec = visibleStartTime;
        double viewEndSec = screenToTime(width);

        for (Integer trackH : trackHeights) {
            trackYPositions.add(currentY);
            int th = trackH;

            g2d.setColor(Color.decode("#0f051d"));
            g2d.fillRect(0, currentY, width, th);
            g2d.setColor(Color.BLACK);
            g2d.drawLine(0, currentY + th - 1, width, currentY + th - 1);

            // Dynamic Grid Lines
            Stroke originalStroke = g2d.getStroke();
            g2d.setStroke(
                    new BasicStroke(1, BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 0, new float[] { 2, 10 }, 0));
            g2d.setColor(Color.decode("#1a0b2e"));

            double step = 1.0;
            if (pixelsPerSecond > 200)
                step = 0.1;
            if (pixelsPerSecond > 800)
                step = 0.05;
            if (pixelsPerSecond < 50)
                step = 5.0;
            if (pixelsPerSecond < 10)
                step = 30.0;

            double startGrid = Math.floor(viewStartSec / step) * step;

            for (double t = startGrid; t < viewEndSec; t += step) {
                int gx = timeToScreen(t);
                if (gx >= 0) {
                    g2d.drawLine(gx, currentY, gx, currentY + th);
                }
            }

            g2d.setStroke(originalStroke);
            currentY += th;
        }

        // Clips - Synchronized copy to prevent
        // flickering/ConcurrentModificationException
        java.util.List<TimelineClip> snapshot;
        synchronized (clips) {
            snapshot = new java.util.ArrayList<>(clips);
        }
        for (TimelineClip clip : snapshot) {
            if (clip.getTrackIndex() < trackYPositions.size()) {
                int trackY = trackYPositions.get(clip.getTrackIndex());
                int trackH = trackHeights.get(clip.getTrackIndex());

                int x = timeToScreen(clip.getStartFrame() / (double) getFPS());
                int w = (int) (clip.getDurationFrames() / (double) getFPS() * pixelsPerSecond);

                if (x + w < 0 || x > width)
                    continue;

                TrackControlPanel.TrackType ttype = (sidebar != null) ? sidebar.getTrackType(clip.getTrackIndex())
                        : null;
                Color bodyCol = (ttype == TrackControlPanel.TrackType.AUDIO) ? TimelineClip.AUDIO_BODY_COLOR
                        : TimelineClip.BODY_COLOR;
                Color headCol = (ttype == TrackControlPanel.TrackType.AUDIO) ? TimelineClip.AUDIO_HEADER_COLOR
                        : TimelineClip.HEADER_COLOR;

                g2d.setColor(bodyCol);
                g2d.fillRect(x, trackY + 1, w, trackH - 2);

                // --- THUMBNAIL RENDERING (Vegas Style) ---
                if (ttype == TrackControlPanel.TrackType.VIDEO) {
                    rocky.core.media.MediaSource source = mediaPool.getSource(clip.getMediaSourceId());
                    if (source != null) {
                        BufferedImage thumb = source.getFrame(clip.getSourceOffsetFrames());
                        if (thumb != null) {
                            int thumbH = trackH - 22;
                            int thumbW = (int) (thumb.getWidth() * ((double) thumbH / thumb.getHeight()));
                            Shape oldClipRect = g2d.getClip();
                            g2d.setClip(new Rectangle(Math.max(0, x), trackY + 21, w, thumbH));
                            g2d.drawImage(thumb, x, trackY + 21, thumbW, thumbH, null);
                            g2d.setClip(oldClipRect);
                        }
                    }
                }

                int headerH = 20;
                g2d.setColor(headCol);
                g2d.fillRect(x, trackY + 1, w, headerH);
                g2d.setColor(Color.BLACK);
                g2d.drawLine(x, trackY + 1 + headerH, x + w, trackY + 1 + headerH);

                int bodyTopY = trackY + 1 + headerH;
                int bodyBottomY = trackY + trackH - 2;
                int bodyH = bodyBottomY - bodyTopY;

                // Safety check
                if (bodyTopY >= bodyBottomY) {
                    bodyTopY = bodyBottomY - 1;
                    bodyH = 1;
                }

                // --- DRAW UNIFIED OPACITY ENVELOPE ---
                drawOpacityEnvelope(g2d, clip, x, w, bodyTopY, bodyH);

                g2d.setColor(Color.WHITE);
                g2d.setFont(new Font("SansSerif", Font.PLAIN, 12));
                Shape oldClip = g2d.getClip();
                g2d.setClip(Math.max(0, x), trackY + 1, Math.min(width, w) - 50, headerH);
                g2d.drawString(clip.getName(), x + 5, trackY + 15);
                g2d.setClip(oldClip);

                int iconW = 24;
                int iconH = 14;
                int iconX = x + w - iconW - 5;
                if (iconX > x + 5) {
                    // FX Label
                    g2d.setColor(Color.decode("#1a0b2e"));
                    g2d.fillRoundRect(iconX, trackY + 3, iconW, iconH, 4, 4);
                    g2d.setColor(Color.WHITE);
                    g2d.drawRoundRect(iconX, trackY + 3, iconW, iconH, 4, 4);
                    g2d.setFont(new Font("SansSerif", Font.BOLD, 10));
                    g2d.drawString("fx", iconX + 6, trackY + 14);

                    // Proxy (px) Label
                    int pxX = iconX - iconW - 5;
                    if (pxX > x + 5) {
                        MediaSource source = mediaPool.getSource(clip.getMediaSourceId());
                        Color pxCol = Color.GRAY;
                        boolean filled = false;

                        if (source != null) {
                            if (source.isProxyActive()) {
                                pxCol = Color.GREEN;
                                filled = true;
                            } else if (source.getProxyFilePath() != null) {
                                pxCol = Color.GREEN;
                            } else if (source.isGeneratingProxy()) {
                                pxCol = Color.YELLOW;
                                filled = true;
                            }
                        }

                        g2d.setColor(filled ? pxCol.darker().darker() : Color.decode("#1a0b2e"));
                        g2d.fillRoundRect(pxX, trackY + 3, iconW, iconH, 4, 4);
                        g2d.setColor(pxCol);
                        g2d.drawRoundRect(pxX, trackY + 3, iconW, iconH, 4, 4);
                        g2d.drawString("px", pxX + 6, trackY + 14);
                    }
                }

                int cornerR = 8;
                // Clip Header Height (defined above)

                // --- DRAW WAVEFORM ---
                if (ttype == TrackControlPanel.TrackType.AUDIO) {
                    MediaSource source = mediaPool.getSource(clip.getMediaSourceId());
                    if (source != null && source.hasAudio()) {
                        float[] peaks = PeakManager.getInstance().getPeaks(source.getId(), source.getFilePath());
                        if (peaks != null) {
                            g2d.setColor(new Color(255, 255, 255, 100)); // Semi-transparent white
                            drawWaveform(g2d, peaks, clip, x, w, bodyTopY, bodyH);
                        }
                    }
                }

                g2d.setColor(Color.WHITE);

                // Fade In Handle (at TOP EDGE) - Cyan rounded handle
                g2d.setColor(Color.CYAN);
                g2d.fillRoundRect(x, bodyTopY - 3, 15, 6, 4, 4);
                g2d.setColor(Color.WHITE);
                g2d.drawRoundRect(x, bodyTopY - 3, 15, 6, 4, 4);

                // Fade Out Handle (at TOP EDGE) - Cyan rounded handle
                g2d.setColor(Color.CYAN);
                g2d.fillRoundRect(x + w - 15, bodyTopY - 3, 15, 6, 4, 4);
                g2d.setColor(Color.WHITE);
                g2d.drawRoundRect(x + w - 15, bodyTopY - 3, 15, 6, 4, 4);

                // Existing Triangles (Resize Handles)
                g2d.setColor(Color.BLUE);
                Polygon triL = new Polygon();
                triL.addPoint(x, bodyBottomY);
                triL.addPoint(x + 8, bodyBottomY);
                triL.addPoint(x, bodyBottomY - 8);
                g2d.fillPolygon(triL);

                Polygon triR = new Polygon();
                triR.addPoint(x + w, bodyBottomY);
                triR.addPoint(x + w - 8, bodyBottomY);
                triR.addPoint(x + w, bodyBottomY - 8);
                g2d.fillPolygon(triR);

                // --- CENTRAL OPACITY HANDLE (at TOP EDGE) ---
                g2d.setColor(Color.CYAN);
                int handleW = 20;
                int handleH = 6;
                int handleX = x + (w / 2) - (handleW / 2);
                if (handleX > x + 18 && handleX < x + w - 18) {
                    g2d.fillRoundRect(handleX, bodyTopY - 3, handleW, handleH, 4, 4);
                    g2d.setColor(Color.WHITE);
                    g2d.drawRoundRect(handleX, bodyTopY - 3, handleW, handleH, 4, 4);
                }
            }
        }

        // Cursors (Hover)
        if (mouseX >= 0) {
            g2d.setColor(HOVER_CURSOR_COLOR);
            Stroke old = g2d.getStroke();
            g2d.setStroke(
                    new BasicStroke(1, BasicStroke.CAP_BUTT, BasicStroke.JOIN_MITER, 10, new float[] { 5, 5 }, 0));
            g2d.drawLine(mouseX, 0, mouseX, height);
            g2d.setStroke(old);
        }

        // Active Playhead Line
        int playheadX = timeToScreen(blueline.getPlayheadFrame() / (double) getFPS());
        if (playheadX >= -20 && playheadX <= width + 20) {
            g2d.setColor(blueline.getColor());
            g2d.drawLine(playheadX, 0, playheadX, height);
        }
    }

    private TexturePaint stipplePaint;

    private void initStipplePattern() {
        if (stipplePaint != null)
            return;
        BufferedImage bi = new BufferedImage(3, 3, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = bi.createGraphics();
        g.setColor(new Color(0, 0, 0, 0)); // Transparent BG
        g.fillRect(0, 0, 3, 3);
        g.setColor(new Color(0, 0, 0, 128)); // Semi-transparent black dots
        g.fillRect(1, 1, 1, 1); // Center dot in 3x3 grid
        g.dispose();
        stipplePaint = new TexturePaint(bi, new Rectangle(0, 0, 3, 3));
    }

    private void drawOpacityEnvelope(Graphics2D g2d, TimelineClip clip, int x, int w, int bodyTopY, int bodyH) {
        if (w <= 0)
            return;

        int res = Math.min(w, 100); // Resolution (max 100 points)
        int[] xPoints = new int[res + 1];
        int[] yPoints = new int[res + 1];
        Polygon fillPoly = new Polygon();

        // Start filling from top corners to create the overlay ABOVE the curve
        fillPoly.addPoint(x, bodyTopY);

        for (int i = 0; i <= res; i++) {
            double progress = (double) i / res;
            int dx = (int) (progress * w);
            long clipFrame = (long) (progress * clip.getDurationFrames());
            double opacity = clip.getOpacityAt(clipFrame);

            int px = x + dx;
            int py = bodyTopY + (int) ((1.0 - opacity) * bodyH);

            xPoints[i] = px;
            yPoints[i] = py;
            fillPoly.addPoint(px, py);
        }

        // Close the polygon at the top right
        fillPoly.addPoint(x + w, bodyTopY);

        // Fill the area ABOVE the curve with stipple pattern
        if (stipplePaint == null)
            initStipplePattern();
        g2d.setPaint(stipplePaint);
        g2d.fillPolygon(fillPoly);

        // Draw the white curve itself
        g2d.setColor(new Color(255, 255, 255, 180));
        g2d.drawPolyline(xPoints, yPoints, res + 1);
    }

    private void drawWaveform(Graphics2D g2d, float[] peaks, TimelineClip clip, int x, int w, int topY, int h) {
        long startFrame = clip.getSourceOffsetFrames();
        long duration = clip.getDurationFrames();

        // We draw one line per pixel (or group of pixels)
        for (int dx = 0; dx < w; dx++) {
            int screenX = x + dx;
            if (screenX < 0 || screenX > getWidth())
                continue;

            // Map pixel to source frame
            double progress = (double) dx / w;
            long sourceFrame = startFrame + (long) (progress * duration);

            if (sourceFrame >= 0 && sourceFrame < peaks.length) {
                float peak = peaks[(int) sourceFrame];
                int peakH = (int) (peak * h * 0.8); // 80% height for margin
                int y1 = topY + (h - peakH) / 2;
                int y2 = y1 + peakH;
                g2d.drawLine(screenX, y1, screenX, y2);
            }
        }
    }

    private double getOpacity(TimelineClip.FadeType type, double t, boolean isFadeIn) {
        return TimelineClip.getOpacity(type, t, isFadeIn);
    }

    private void zoomIn(double anchorTime, double factor) {
        double oldPPS = pixelsPerSecond;
        pixelsPerSecond *= factor;
        if (pixelsPerSecond > MAX_ZOOM)
            pixelsPerSecond = MAX_ZOOM;

        applyZoomCentering(anchorTime, oldPPS);
    }

    private void zoomOut(double anchorTime, double factor) {
        double oldPPS = pixelsPerSecond;
        pixelsPerSecond /= factor;
        if (pixelsPerSecond < MIN_ZOOM)
            pixelsPerSecond = MIN_ZOOM;

        applyZoomCentering(anchorTime, oldPPS);
    }

    private void applyZoomCentering(double anchorTime, double oldPPS) {
        // We want anchorTime to stay at the same screen position
        // ScreenPos = (time - visibleStart) * oldPPS
        // ScreenPos = (time - newVisibleStart) * newPPS
        // newVisibleStart = time - (ScreenPos / newPPS)

        int screenX = (mouseX >= 0) ? mouseX : getWidth() / 2;
        visibleStartTime = anchorTime - (screenX / pixelsPerSecond);
        if (visibleStartTime < 0)
            visibleStartTime = 0;

        fireTimelineUpdated();
    }

    public void fireTimelineUpdated() {
        for (TimelineListener listener : listeners) {
            listener.onTimeUpdate(getPlayheadTime(), getPlayheadFrame(), blueline.formatTimecode(getPlayheadFrame()),
                    true);
            listener.onTimelineUpdated();
        }
        repaint();
    }

    public long getLayoutRevision() {
        return layoutRevision.get();
    }
}
