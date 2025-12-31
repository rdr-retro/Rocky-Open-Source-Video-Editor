package b.timeline;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import egine.media.PeakManager;
import egine.media.MediaSource;

public class TimelinePanel extends JPanel {
    private int mouseX = -1; // Hover cursor position
    private long playheadFrame = 0; // Active Playhead Time (Source of Truth)
    // Removed: javax.swing.Timer playbackTimer; (Handled by AudioServer as Master Clock)

    private boolean isPlaying = false;
    
    private final int FPS = 30;
    
    // View State
    private double pixelsPerSecond = 100.0; // Dynamic Zoom Scale
    private double visibleStartTime = 0.0; // Time at X=0 (in seconds)
    
    // Limits
    private final double MIN_ZOOM = 1.0;    
    private final double MAX_ZOOM = 1000.0; 
    
    // Project Settings
    private double projectDuration = 300.0; // Seconds (Default 5 mins)
    
    // Colors
    private final Color BG_COLOR = Color.decode("#1e1e1e"); 
    private final Color HOVER_CURSOR_COLOR = Color.decode("#d4d4d4"); 
    private final Color PLAYHEAD_COLOR = Color.decode("#54a0ff"); 

    // Media
    private egine.media.MediaPool mediaPool;
    private SidebarPanel sidebar;
    
    public void setSidebar(SidebarPanel sidebar) {
        this.sidebar = sidebar;
    }

    public TrackControlPanel.TrackType getTrackType(int index) {
        if (sidebar != null) return sidebar.getTrackType(index);
        return null;
    }

    // Clips
    private java.util.List<TimelineClip> clips = new java.util.ArrayList<>();

    // --- PUBLIC ACCESSORS FOR RULER ---
    public double getPixelsPerSecond() { return pixelsPerSecond; }
    public double getVisibleStartTime() { return visibleStartTime; }
    public long getPlayheadFrame() { return playheadFrame; }
    public java.util.List<TimelineClip> getClips() { 
        synchronized(clips) {
            return new java.util.ArrayList<>(clips); 
        }
    }
    public java.util.List<Integer> getTrackHeights() { return trackHeights; }
    
    public void setMediaPool(egine.media.MediaPool pool) { this.mediaPool = pool; }
    public void clearClips() { synchronized(clips) { clips.clear(); } repaint(); }
    public void addClip(TimelineClip clip) { synchronized(clips) { clips.add(clip); } repaint(); }
    
    // --- ACCESSORS FOR SCROLLBAR ---
    public long getContentDurationFrames() {
        long maxFrame = 0;
        for (TimelineClip clip : clips) {
            long end = clip.getStartFrame() + clip.getDurationFrames();
            if (end > maxFrame) maxFrame = end;
        }
        return maxFrame;
    }

    public double getProjectDuration() {
        // Calculate dynamic duration based on content
        double maxTime = 300.0; // Minimum 5 minutes
        for (TimelineClip clip : clips) {
            double end = (clip.getStartFrame() + clip.getDurationFrames()) / (double)FPS;
            if (end > maxTime) maxTime = end;
        }
        // Add some padding at the end (e.g. 1 minute)
        return maxTime + 60.0;
    }
    
    public double getVisibleDuration() {
        if (pixelsPerSecond <= 0) return 0;
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
        this.playheadFrame = frame;
        double time = frame / (double) FPS;
        if (timeListener != null) {
            timeListener.onTimeUpdate(time, frame, formatTimecode(frame));
            timeListener.onTimelineUpdated();
        }
        repaint();
    }

    public boolean isPlaying() { return isPlaying; }

    public void togglePlayback() {
        if (isPlaying) {
            stopPlayback();
        } else {
            startPlayback();
        }
    }

    public void startPlayback() {
        // Playback is now driven by AudioServer
        isPlaying = true;
    }

    public void stopPlayback() {
        isPlaying = false;
    }

    public TimelinePanel() {
        setBackground(BG_COLOR);
        PeakManager.getInstance().addUpdateListener(() -> repaint());
        
        MouseAdapter interactionHandler = new MouseAdapter() {
            private final int RESIZE_MARGIN = 10;
            private TimelineClip activeClip = null;
            private int interactionMode = 0; 
            private int dragStartX = 0;
            private long originalStart = 0;
            private long originalDuration = 0;

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
                            int clipX = timeToScreen(clip.getStartFrame() / (double)FPS);
                            int clipW = (int)(clip.getDurationFrames() / (double)FPS * pixelsPerSecond);
                            
                            if (mouseY >= currentY && mouseY < currentY + trackH) {
                            int headerH = 20; 
                            int bodyTopY = currentY + headerH;
                            
                            // Fade Handle Detection
                            int handleSize = 12;
                            // Fade In
                            if (mouseY >= bodyTopY && mouseY <= bodyTopY + handleSize &&
                                e.getX() >= clipX && e.getX() <= clipX + handleSize) {
                                setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
                                cursorSet = true;
                            // Fade Out
                            } else if (mouseY >= bodyTopY && mouseY <= bodyTopY + handleSize &&
                                e.getX() >= clipX + clipW - handleSize && e.getX() <= clipX + clipW) {
                                setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
                                cursorSet = true;
                            } else if (Math.abs(e.getX() - clipX) <= RESIZE_MARGIN) {
                                setCursor(Cursor.getPredefinedCursor(Cursor.W_RESIZE_CURSOR));
                                cursorSet = true;
                            } else if (Math.abs(e.getX() - (clipX + clipW)) <= RESIZE_MARGIN) {
                                setCursor(Cursor.getPredefinedCursor(Cursor.E_RESIZE_CURSOR));
                                cursorSet = true;
                            } else if (e.getX() > clipX && e.getX() < clipX + clipW) {
                                setCursor(Cursor.getPredefinedCursor(Cursor.MOVE_CURSOR)); 
                                cursorSet = true;
                            }
                        }
                    }
                }
                currentY += trackH;
            }
            
            if (!cursorSet) setCursor(Cursor.getDefaultCursor());
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
                         int clipX = timeToScreen(clip.getStartFrame() / (double)FPS);
                         int clipW = (int)(clip.getDurationFrames() / (double)FPS * pixelsPerSecond);
                         
                         int headerH = 20; 
                         int bodyTopY = currentY + headerH;
                         
                         if (mouseY >= currentY && mouseY < currentY + trackH) {
                             int handleSize = 12;
                             
                             // Fade In Handle (Top-Left of BODY)
                             // Y Range: [bodyTopY, bodyTopY + handleSize]
                             // X Range: [clipX, clipX + handleSize]
                             if (mouseY >= bodyTopY && mouseY <= bodyTopY + handleSize &&
                                 mouseX >= clipX && mouseX <= clipX + handleSize) {
                                 startInteraction(clip, 5, mouseX); // Mode 5 = FADE IN
                                 return;
                             }

                             // Fade Out Handle (Top-Right of BODY)
                             // Y Range: [bodyTopY, bodyTopY + handleSize]
                             // X Range: [clipX + clipW - handleSize, clipX + clipW]
                             if (mouseY >= bodyTopY && mouseY <= bodyTopY + handleSize &&
                                 mouseX >= clipX + clipW - handleSize && mouseX <= clipX + clipW) {
                                 startInteraction(clip, 4, mouseX); // Mode 4 = FADE OUT
                                 return;
                             }
                             
                             if (Math.abs(mouseX - clipX) <= RESIZE_MARGIN) {
                                 startInteraction(clip, 2, mouseX);
                                 return;
                             } else if (Math.abs(mouseX - (clipX + clipW)) <= RESIZE_MARGIN) {
                                 startInteraction(clip, 3, mouseX);
                                 return;
                             } else if (mouseX > clipX && mouseX < clipX + clipW) {
                                 startInteraction(clip, 1, mouseX);
                                 updatePlayhead(mouseX); 
                                 return;
                             }
                         }
                    }
                }
                currentY += trackH;
            }
            
            if (activeClip == null) {
                updatePlayhead(mouseX);
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
        }

        @Override
        public void mouseDragged(MouseEvent e) {
            if (activeClip != null) {
                int deltaX = e.getX() - dragStartX;
                double deltaSecs = deltaX / pixelsPerSecond;
                long deltaFrames = (long) (deltaSecs * FPS);
                
                if (interactionMode == 1) { 
                    activeClip.setStartFrame(Math.max(0, originalStart + deltaFrames));
                    if (timeListener != null) timeListener.onTimelineUpdated();
                } else if (interactionMode == 2) { 
                    long newStart = Math.max(0, originalStart + deltaFrames);
                    long endFrame = originalStart + originalDuration;
                    if (newStart < endFrame - 5) {
                        activeClip.setStartFrame(newStart);
                        activeClip.setDurationFrames(endFrame - newStart);
                    }
                    if (timeListener != null) timeListener.onTimelineUpdated();
                } else if (interactionMode == 3) { 
                    long newDuration = Math.max(5, originalDuration + deltaFrames);
                    activeClip.setDurationFrames(newDuration);
                    if (timeListener != null) timeListener.onTimelineUpdated();
                } else if (interactionMode == 4) { // FADE OUT
                    long newFade = originalFadeOut - deltaFrames;
                    if (newFade < 0) newFade = 0;
                    if (newFade > activeClip.getDurationFrames() - activeClip.getFadeInFrames()) 
                        newFade = activeClip.getDurationFrames() - activeClip.getFadeInFrames();
                    activeClip.setFadeOutFrames(newFade);
                    // No global update needed
                } else if (interactionMode == 5) { // FADE IN
                     // Drag Right (Positive delta) -> Increase Fade
                    long newFade = originalFadeIn + deltaFrames;
                    if (newFade < 0) newFade = 0;
                    if (newFade > activeClip.getDurationFrames() - activeClip.getFadeOutFrames()) 
                        newFade = activeClip.getDurationFrames() - activeClip.getFadeOutFrames();
                    activeClip.setFadeInFrames(newFade);
                    // No global update needed
                }
                
                repaint();
            } else {
                mouseX = e.getX();
                updatePlayhead(mouseX);
            }
        }

            @Override
            public void mouseReleased(MouseEvent e) {
                if (e.isPopupTrigger() || SwingUtilities.isRightMouseButton(e)) {
                   handleCallback(e);
                } else {
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
                            int clipX = timeToScreen(clip.getStartFrame() / (double)FPS);
                            int clipW = (int)(clip.getDurationFrames() / (double)FPS * pixelsPerSecond);
                            
                            int headerH = 20; 
                            int bodyTopY = currentY + headerH;
                            
                            if (mouseY >= currentY && mouseY < currentY + trackH) {
                                // Check if click is in Fade In Area
                                // Simple approximate check: left side of clip within fade width
                                int fadeInW = (int)(clip.getFadeInFrames() / (double)FPS * pixelsPerSecond);
                                if (fadeInW > 5 && mouseX >= clipX && mouseX <= clipX + fadeInW && mouseY >= bodyTopY) {
                                    showFadeMenu(e, clip, true);
                                    return;
                                }
                                
                                // Check Fade Out Area
                                int fadeOutW = (int)(clip.getFadeOutFrames() / (double)FPS * pixelsPerSecond);
                                if (fadeOutW > 5 && mouseX >= clipX + clipW - fadeOutW && mouseX <= clipX + clipW && mouseY >= bodyTopY) {
                                    showFadeMenu(e, clip, false);
                                    return;
                                }
                            }
                        }
                    }
                    currentY += trackH;
                }
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
                        type.toString().charAt(0) + type.toString().substring(1).toLowerCase()
                    );
                    if (type == currentType) item.setSelected(true);
                    item.addActionListener(ev -> {
                        if (isFadeIn) clip.setFadeInType(type);
                        else clip.setFadeOutType(type);
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
        
        // ZOOM / PAN - Simplified (Only Zoom)
        addMouseWheelListener(e -> {
            boolean isCtrl = e.isControlDown() || e.isMetaDown();
            double mouseTime = screenToTime(e.getX());
            
            if (isCtrl) {
                double zoomFactor = 1.1; 
                if (e.getPreciseWheelRotation() > 0) pixelsPerSecond /= zoomFactor;
                else pixelsPerSecond *= zoomFactor;
                
                if (pixelsPerSecond < MIN_ZOOM) pixelsPerSecond = MIN_ZOOM;
                if (pixelsPerSecond > MAX_ZOOM) pixelsPerSecond = MAX_ZOOM;
                
                visibleStartTime = mouseTime - (e.getX() / pixelsPerSecond);
                if (visibleStartTime < 0) visibleStartTime = 0;
                
                if (timeListener != null) timeListener.onTimelineUpdated();
                repaint();
            } else {
                // If not locked in JScrollPane, this handles pan. But JScrollPane should handle Pan?
                // Let's allow Wheel pan to update visibility, but we need to notify scrollbar...
                // Ideally, horizontal wheel scrolling should be handled by JScrollPane
                // But for "Vegas" feel of simple vertical wheel = horizontal pan:
                
                double scrollAmount = (getWidth() / pixelsPerSecond) * 0.1 * e.getPreciseWheelRotation();
                visibleStartTime += scrollAmount;
                if (visibleStartTime < 0) visibleStartTime = 0;
                
                if (timeListener != null) timeListener.onTimelineUpdated(); // Sync scrollbar
                repaint();
            }
        });
        
        // Drop Traget
        setDropTarget(new java.awt.dnd.DropTarget(this, new java.awt.dnd.DropTargetListener() {
            public void dragEnter(java.awt.dnd.DropTargetDragEvent dtde) {}
            public void dragOver(java.awt.dnd.DropTargetDragEvent dtde) {}
            public void dropActionChanged(java.awt.dnd.DropTargetDragEvent dtde) {}
            public void dragExit(java.awt.dnd.DropTargetEvent dte) {}
            @Override
            public void drop(java.awt.dnd.DropTargetDropEvent dtde) {
                try {
                    dtde.acceptDrop(java.awt.dnd.DnDConstants.ACTION_COPY);
                    java.util.List<java.io.File> droppedFiles = (java.util.List<java.io.File>)
                            dtde.getTransferable().getTransferData(java.awt.datatransfer.DataFlavor.javaFileListFlavor);
                    
                    if (droppedFiles != null && !droppedFiles.isEmpty()) {
                        java.io.File file = droppedFiles.get(0); 
                        String name = file.getName();
                        
                        Point loc = dtde.getLocation();
                        double droppedTime = screenToTime(loc.x);
                        long startFrame = (long) (droppedTime * FPS);
                        
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
                        
                        // If dropping into an empty timeline or empty area below tracks, create a NEW Video track
                        if (targetTrackIndex == -1 && sidebar != null) {
                            sidebar.addTrack(TrackControlPanel.TrackType.VIDEO);
                            targetTrackIndex = sidebar.getTrackCount() - 1;
                        }
                        
                        if (targetTrackIndex != -1) {
                            String mediaId = name; 
                            if (mediaPool != null) {
                                egine.media.MediaSource source = mediaPool.getSource(mediaId);
                                if (source == null) {
                                    source = new egine.media.MediaSource(mediaId, file.getAbsolutePath());
                                    mediaPool.addSource(source);
                                }

                                long duration = (source.getTotalFrames() > 0) ? source.getTotalFrames() : 5 * FPS;
                                TrackControlPanel.TrackType trackType = (sidebar != null) ? sidebar.getTrackType(targetTrackIndex) : null;
                                
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

                                TimelineClip clip = new TimelineClip(name, startFrame, duration, targetTrackIndex);
                                clip.setMediaSourceId(mediaId);
                                synchronized(clips) {
                                    clips.add(clip);
                                }

                                // Rule 3: MP4/Video with audio -> Auto create audio track below
                                // We check source.hasAudio() which now uses the more reliable AudioDecoder probe
                                boolean hasAudio = source.hasAudio();
                                System.out.println("[Drop] Processing " + name + " (Video: " + source.isVideo() + ", Audio: " + hasAudio + ")");

                                if (source.isVideo() && hasAudio && trackType == TrackControlPanel.TrackType.VIDEO) {
                                    if (sidebar != null) {
                                        int audioTrackIdx = targetTrackIndex + 1;
                                        System.out.println("[Drop] Auto-creating audio track for " + name + " at index: " + audioTrackIdx);
                                        
                                        // 1. Shift existing clips in TimelinePanel
                                        onTrackInserted(audioTrackIdx);
                                        // 2. Insert the track in SidebarPanel
                                        sidebar.addTrack(TrackControlPanel.TrackType.AUDIO, audioTrackIdx);
                                        
                                        TimelineClip audioClip = new TimelineClip(name + " (Audio)", startFrame, duration, audioTrackIdx);
                                        audioClip.setMediaSourceId(mediaId);
                                        synchronized(clips) {
                                            clips.add(audioClip);
                                        }
                                    }
                                }
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
        double time = screenToTime(x);
        playheadFrame = (long) (time * FPS);
        if (playheadFrame < 0) playheadFrame = 0;
        
        if (timeListener != null) {
            timeListener.onTimeUpdate(time, playheadFrame, formatTimecode(playheadFrame));
            timeListener.onTimelineUpdated(); // Request Repaint of Ruler
        }
        repaint();
    }

    private java.util.List<Integer> trackHeights = new java.util.ArrayList<>();
    
    public void setTrackHeights(java.util.List<Integer> heights) {
        this.trackHeights = heights;
        int totalH = 0; 
        for (int h : heights) totalH += h;
        
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
        synchronized(clips) {
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
        repaint();
    }

    /**
     * Shifts clips down when a new track is inserted in the middle.
     */
    public void onTrackInserted(int index) {
        synchronized(clips) {
            for (TimelineClip clip : clips) {
                if (clip.getTrackIndex() >= index) {
                    clip.setTrackIndex(clip.getTrackIndex() + 1);
                }
            }
        }
        repaint();
    }
    
    public interface TimelineListener {
        void onTimeUpdate(double timeInSeconds, long totalFrames, String timecode);
        void onTimelineUpdated(); // For syncing ruler/scrollbar
    }
    
    private TimelineListener timeListener;
    
    public void setTimelineListener(TimelineListener listener) {
        this.timeListener = listener;
    }

    private String formatTimecode(long totalFrames) {
        long frames = totalFrames % FPS;
        long totalSeconds = totalFrames / FPS;
        long seconds = totalSeconds % 60;
        long minutes = (totalSeconds / 60) % 60;
        long hours = totalSeconds / 3600;
        return String.format("%02d:%02d:%02d;%02d", hours, minutes, seconds, frames);
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
            
            g2d.setColor(Color.decode("#222222")); 
            g2d.fillRect(0, currentY, width, th);
            g2d.setColor(Color.BLACK);
            g2d.drawLine(0, currentY + th - 1, width, currentY + th - 1);
            
            // Dynamic Grid Lines
            Stroke originalStroke = g2d.getStroke();
            g2d.setStroke(new BasicStroke(1, BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 0, new float[]{2, 10}, 0));
            g2d.setColor(Color.decode("#333333")); 
             
            double step = 1.0; 
            if (pixelsPerSecond > 200) step = 0.1;
            if (pixelsPerSecond > 800) step = 0.05;
            if (pixelsPerSecond < 50) step = 5.0; 
            if (pixelsPerSecond < 10) step = 30.0;
            
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
        
        // Clips
        for (TimelineClip clip : clips) {
            if (clip.getTrackIndex() < trackYPositions.size()) {
                int trackY = trackYPositions.get(clip.getTrackIndex());
                int trackH = trackHeights.get(clip.getTrackIndex());
                
                int x = timeToScreen(clip.getStartFrame() / (double)FPS);
                int w = (int)(clip.getDurationFrames() / (double)FPS * pixelsPerSecond);
                
                if (x + w < 0 || x > width) continue; 
                
                TrackControlPanel.TrackType ttype = (sidebar != null) ? sidebar.getTrackType(clip.getTrackIndex()) : null;
                Color bodyCol = (ttype == TrackControlPanel.TrackType.AUDIO) ? TimelineClip.AUDIO_BODY_COLOR : TimelineClip.BODY_COLOR;
                Color headCol = (ttype == TrackControlPanel.TrackType.AUDIO) ? TimelineClip.AUDIO_HEADER_COLOR : TimelineClip.HEADER_COLOR;

                g2d.setColor(bodyCol);
                g2d.fillRect(x, trackY + 1, w, trackH - 2);
                
                int headerH = 20;
                g2d.setColor(headCol);
                g2d.fillRect(x, trackY + 1, w, headerH);
                g2d.setColor(Color.BLACK);
                g2d.drawRect(x, trackY + 1, w, trackH - 2);
                g2d.drawLine(x, trackY + 1 + headerH, x + w, trackY + 1 + headerH); 
                
                g2d.setColor(Color.WHITE);
                g2d.setFont(new Font("SansSerif", Font.PLAIN, 12));
                Shape oldClip = g2d.getClip();
                g2d.setClip(Math.max(0, x), trackY + 1, Math.min(width, w) - 50, headerH); 
                g2d.drawString(clip.getName(), x + 5, trackY + 15);
                g2d.setClip(oldClip);
                
                int iconX = x + w - 50; 
                if (iconX > x) {
                    g2d.setFont(new Font("SansSerif", Font.BOLD, 10));
                    g2d.drawString("crop", iconX, trackY + 14);
                    g2d.drawString("fx", iconX + 25, trackY + 14);
                }
                
                int cornerR = 8;
                // Clip Header Height (defined above)
                int bodyTopY = trackY + 1 + headerH;
                int bodyBottomY = trackY + trackH - 2;
                int bodyH = bodyBottomY - bodyTopY;
                
                // Safety check
                if (bodyTopY >= bodyBottomY) {
                    bodyTopY = bodyBottomY - 1;
                    bodyH = 1;
                }

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
                int handleSize = 12;

                // Draw Fade In Curve & Handle
                if (clip.getFadeInFrames() > 0) {
                    double fadeDurationSec = clip.getFadeInFrames() / (double)FPS;
                    int fadeW = (int) (fadeDurationSec * pixelsPerSecond);
                    int fadeEndX = x + fadeW;
                    
                    // Render Curve using Polyline
                    drawFadeCurve(g2d, clip.getFadeInType(), true, x, fadeW, bodyTopY, bodyH);
                }
                
                // Fade In Handle (Top-Left of BODY) - Cyan
                g2d.setColor(Color.CYAN); 
                g2d.drawArc(x - handleSize, bodyTopY - handleSize, handleSize*2, handleSize*2, 270, 90);

                // Draw Fade Out Curve & Handle
                if (clip.getFadeOutFrames() > 0) {
                    double fadeDurationSec = clip.getFadeOutFrames() / (double)FPS;
                    int fadeW = (int) (fadeDurationSec * pixelsPerSecond);
                    int fadeStartX = x + w - fadeW;
                    
                    // Render Curve using Polyline
                    drawFadeCurve(g2d, clip.getFadeOutType(), false, fadeStartX, fadeW, bodyTopY, bodyH);
                }
                
                // Fade Out Handle (Top-Right of BODY) - Cyan
                g2d.setColor(Color.CYAN); 
                g2d.drawArc(x + w - handleSize, bodyTopY - handleSize, handleSize*2, handleSize*2, 180, 90);
                
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
            }
        }
        
        // Cursors (Hover)
        if (mouseX >= 0) {
            g2d.setColor(HOVER_CURSOR_COLOR);
            Stroke old = g2d.getStroke();
            g2d.setStroke(new BasicStroke(1, BasicStroke.CAP_BUTT, BasicStroke.JOIN_MITER, 10, new float[]{5, 5}, 0)); 
            g2d.drawLine(mouseX, 0, mouseX, height);
            g2d.setStroke(old);
        }
        
        // Active Playhead Line
        int playheadX = timeToScreen(playheadFrame / (double) FPS);
        if (playheadX >= -20 && playheadX <= width + 20) {
            g2d.setColor(PLAYHEAD_COLOR);
            g2d.drawLine(playheadX, 0, playheadX, height);
        }
    }
    
    private TexturePaint stipplePaint;
    
    private void initStipplePattern() {
        if (stipplePaint != null) return;
        BufferedImage bi = new BufferedImage(3, 3, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = bi.createGraphics();
        g.setColor(new Color(0, 0, 0, 0)); // Transparent BG
        g.fillRect(0, 0, 3, 3);
        g.setColor(new Color(0, 0, 0, 128)); // Semi-transparent black dots
        g.fillRect(1, 1, 1, 1); // Center dot in 3x3 grid
        g.dispose();
        stipplePaint = new TexturePaint(bi, new Rectangle(0, 0, 3, 3));
    }

    private void drawFadeCurve(Graphics2D g2d, TimelineClip.FadeType type, boolean isFadeIn, int startX, int width, int topY, int height) {
        if (width <= 0) return;
        
        initStipplePattern();
        
        int step = 2; // Pixel step for optimization
        int points = (int) Math.ceil((double)width / step) + 1;
        int[] xPoints = new int[points];
        int[] yPoints = new int[points];
        
        // Polygon for Fill (Transparency Area - Above Curve)
        Polygon fillPoly = new Polygon();
        fillPoly.addPoint(startX, topY); // Top-Left corner of bounding box
        
        int idx = 0;
        for (int dx = 0; dx <= width; dx += step) {
            if (dx > width) dx = width; // Ensure end point
            double t = (double)dx / width;
            double opacity = getOpacity(type, t, isFadeIn);
            
            xPoints[idx] = startX + dx;
            // Map Opacity 1.0 -> topY, 0.0 -> topY + height (bottom)
            int y = topY + (int)((1.0 - opacity) * height);
            yPoints[idx] = y;
            fillPoly.addPoint(xPoints[idx], yPoints[idx]);
            
            idx++;
            if (dx == width) break;
        }
        
        // Handle last point if missed
        if (idx < points) {
             xPoints[idx] = startX + width;
             double opacity = getOpacity(type, 1.0, isFadeIn);
             int y = topY + (int)((1.0 - opacity) * height);
             yPoints[idx] = y;
             fillPoly.addPoint(xPoints[idx], yPoints[idx]);
             points = idx + 1;
        } else {
             points = idx;
        }
        
        // Close the Polygon
        // We added Top-Left. Then traced curve (Left to Right).
        // Now add Top-Right.
        fillPoly.addPoint(startX + width, topY);
        
        // Fill Stipple Pattern
        Paint oldPaint = g2d.getPaint();
        g2d.setPaint(stipplePaint);
        g2d.fillPolygon(fillPoly);
        g2d.setPaint(oldPaint);

        Stroke oldStroke = g2d.getStroke();
        g2d.setStroke(new BasicStroke(2.0f));
        g2d.drawPolyline(xPoints, yPoints, points);
        g2d.setStroke(oldStroke);
    }

    private void drawWaveform(Graphics2D g2d, float[] peaks, TimelineClip clip, int x, int w, int topY, int h) {
        long startFrame = clip.getSourceOffsetFrames();
        long duration = clip.getDurationFrames();
        
        // We draw one line per pixel (or group of pixels)
        for (int dx = 0; dx < w; dx++) {
            int screenX = x + dx;
            if (screenX < 0 || screenX > getWidth()) continue;
            
            // Map pixel to source frame
            double progress = (double)dx / w;
            long sourceFrame = startFrame + (long)(progress * duration);
            
            if (sourceFrame >= 0 && sourceFrame < peaks.length) {
                float peak = peaks[(int)sourceFrame];
                int peakH = (int)(peak * h * 0.8); // 80% height for margin
                int y1 = topY + (h - peakH) / 2;
                int y2 = y1 + peakH;
                g2d.drawLine(screenX, y1, screenX, y2);
            }
        }
    }

    private double getOpacity(TimelineClip.FadeType type, double t, boolean isFadeIn) {
        return TimelineClip.getOpacity(type, t, isFadeIn);
    }
}
