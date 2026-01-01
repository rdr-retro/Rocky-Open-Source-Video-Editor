package rocky.ui.keyframes;

import rocky.ui.timeline.TimelineClip;
import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.util.Comparator;

/**
 * A professional miniature timeline for managing keyframes.
 * Matches the reference image style.
 */
public class KeyframeTimelinePanel extends JPanel {
    private final TimelineClip clip;

    // UI Constants
    private final int SIDEBAR_WIDTH = 120;
    private final int RULER_HEIGHT = 28;
    private final int TOOLBAR_HEIGHT = 45;
    private final int TRACK_HEIGHT = 24;

    // Colors (Matched to reference)
    private final Color BG_COLOR_DARK = Color.decode("#0f051d");
    private final Color SIDEBAR_BG = Color.decode("#1a0b2e");
    private final Color TRACK_BG = Color.decode("#0f051d");
    private final Color RULER_BG = Color.decode("#1a0b2e");
    private final Color ACCENT_LILAC = Color.decode("#dcd0ff");
    private final Color ACCENT_PURPLE = Color.decode("#9d50bb");
    private final Color ICON_COLOR = Color.decode("#dcd0ff");

    private long localPlayheadFrame = 0;
    private TimelineKeyframe selectedKeyframe = null;
    private boolean isScrubbing = false;

    private TimelineListener timelineListener;

    public interface TimelineListener {
        void onPlayheadChanged(long frame);
    }

    public void setTimelineListener(TimelineListener l) {
        this.timelineListener = l;
    }

    public KeyframeTimelinePanel(TimelineClip clip) {
        this.clip = clip;
        setBackground(BG_COLOR_DARK);
        setPreferredSize(new Dimension(800, 220));

        MouseAdapter ma = new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                int x = e.getX();
                int y = e.getY();
                int h = getHeight();

                // Scrubbing playhead
                if (y < RULER_HEIGHT) {
                    isScrubbing = true;
                    localPlayheadFrame = xToClipFrame(x);
                    if (timelineListener != null)
                        timelineListener.onPlayheadChanged(localPlayheadFrame);
                    repaint();
                    return;
                }

                // Toolbar interaction
                if (y > h - TOOLBAR_HEIGHT) {
                    handleToolbarClick(x, y);
                    repaint();
                    return;
                }

                // Mask toggle interaction
                if (x < SIDEBAR_WIDTH && y > RULER_HEIGHT + TRACK_HEIGHT && y < RULER_HEIGHT + TRACK_HEIGHT * 2) {
                    clip.getMask().setEnabled(!clip.getMask().isEnabled());
                    repaint();
                    return;
                }

                // Keyframe interaction
                selectedKeyframe = findKeyframeAt(x, y);
                if (SwingUtilities.isRightMouseButton(e) && selectedKeyframe != null) {
                    if (selectedKeyframe.getClipFrame() > 0
                            && selectedKeyframe.getClipFrame() < clip.getDurationFrames()) {
                        clip.getTimeKeyframes().remove(selectedKeyframe);
                        selectedKeyframe = null;
                        repaint();
                    }
                } else if (e.getClickCount() == 2 && selectedKeyframe == null && x > SIDEBAR_WIDTH) {
                    long cf = xToClipFrame(x);
                    TimelineKeyframe k = new TimelineKeyframe(cf, cf, clip.getTransform());
                    clip.getTimeKeyframes().add(k);
                    selectedKeyframe = k;
                    repaint();
                }
            }

            @Override
            public void mouseDragged(MouseEvent e) {
                if (isScrubbing) {
                    localPlayheadFrame = xToClipFrame(e.getX());
                    if (timelineListener != null)
                        timelineListener.onPlayheadChanged(localPlayheadFrame);
                    repaint();
                } else if (selectedKeyframe != null) {
                    long cf = xToClipFrame(e.getX());
                    if (cf < 0)
                        cf = 0;
                    if (cf > clip.getDurationFrames())
                        cf = clip.getDurationFrames();

                    if (selectedKeyframe.getClipFrame() > 0
                            && selectedKeyframe.getClipFrame() < clip.getDurationFrames()) {
                        selectedKeyframe.setClipFrame(cf);
                    }
                    repaint();
                }
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                isScrubbing = false;
                selectedKeyframe = null;
            }
        };

        addMouseListener(ma);
        addMouseMotionListener(ma);
    }

    private void handleToolbarClick(int x, int y) {
        int iconX = 60; // Offset for icons

        // Navigation: Prev
        if (x >= iconX && x < iconX + 40) {
            TimelineKeyframe prev = null;
            for (TimelineKeyframe k : clip.getTimeKeyframes()) {
                if (k.getClipFrame() < localPlayheadFrame) {
                    if (prev == null || k.getClipFrame() > prev.getClipFrame())
                        prev = k;
                }
            }
            if (prev != null) {
                localPlayheadFrame = prev.getClipFrame();
                if (timelineListener != null)
                    timelineListener.onPlayheadChanged(localPlayheadFrame);
            }
        }
        // Navigation: Next
        else if (x >= iconX + 40 && x < iconX + 80) {
            TimelineKeyframe next = null;
            for (TimelineKeyframe k : clip.getTimeKeyframes()) {
                if (k.getClipFrame() > localPlayheadFrame) {
                    if (next == null || k.getClipFrame() < next.getClipFrame())
                        next = k;
                }
            }
            if (next != null) {
                localPlayheadFrame = next.getClipFrame();
                if (timelineListener != null)
                    timelineListener.onPlayheadChanged(localPlayheadFrame);
            }
        }
        // Add Keyframe at Playhead
        else if (x >= iconX + 80 && x < iconX + 120) {
            if (findKeyframeAt(clipFrameToX(localPlayheadFrame), RULER_HEIGHT + TRACK_HEIGHT / 2) == null) {
                clip.getTimeKeyframes().add(new TimelineKeyframe(localPlayheadFrame, localPlayheadFrame, clip.getTransform()));
            }
        }
        // Remove selected/under playhead keyframe
        else if (x >= iconX + 120 && x < iconX + 160) {
            TimelineKeyframe toRemove = selectedKeyframe;
            if (toRemove == null)
                toRemove = findKeyframeAt(clipFrameToX(localPlayheadFrame), RULER_HEIGHT + TRACK_HEIGHT / 2);

            if (toRemove != null && toRemove.getClipFrame() > 0 && toRemove.getClipFrame() < clip.getDurationFrames()) {
                clip.getTimeKeyframes().remove(toRemove);
                if (selectedKeyframe == toRemove)
                    selectedKeyframe = null;
            }
        }
    }

    private TimelineKeyframe findKeyframeAt(int x, int y) {
        if (x < SIDEBAR_WIDTH)
            return null;
        for (TimelineKeyframe k : clip.getTimeKeyframes()) {
            int kx = clipFrameToX(k.getClipFrame());
            int ky = RULER_HEIGHT + (TRACK_HEIGHT / 2);
            if (Math.abs(x - kx) < 8 && Math.abs(y - ky) < 8)
                return k;
        }
        return null;
    }

    private int clipFrameToX(long f) {
        int timelineWidth = getWidth() - SIDEBAR_WIDTH;
        if (timelineWidth <= 0)
            return 0;
        double ratio = (double) f / clip.getDurationFrames();
        return SIDEBAR_WIDTH + (int) (ratio * (timelineWidth - 10));
    }

    private long xToClipFrame(int x) {
        int timelineWidth = getWidth() - SIDEBAR_WIDTH;
        if (timelineWidth <= 0)
            return 0;
        double ratio = (double) (x - SIDEBAR_WIDTH) / (timelineWidth - 10);
        long f = Math.round(ratio * clip.getDurationFrames());
        return Math.max(0, Math.min(f, clip.getDurationFrames()));
    }

    private String formatTC(long frames) {
        long f = frames % 30;
        long s = (frames / 30) % 60;
        long m = (frames / 1800) % 60;
        long h = frames / 108000;
        return String.format("%02d:%02d:%02d;%02d", h, m, s, f);
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g;
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int w = getWidth();
        int h = getHeight();

        // 1. Sidebar Background
        g2.setColor(SIDEBAR_BG);
        g2.fillRect(0, 0, SIDEBAR_WIDTH, h);
        g2.setColor(Color.BLACK);
        g2.drawLine(SIDEBAR_WIDTH - 1, 0, SIDEBAR_WIDTH - 1, h);

        // 2. Track Area Background
        g2.setColor(TRACK_BG);
        g2.fillRect(SIDEBAR_WIDTH, RULER_HEIGHT, w - SIDEBAR_WIDTH, TRACK_HEIGHT);
        g2.setColor(Color.BLACK);
        g2.drawLine(SIDEBAR_WIDTH, RULER_HEIGHT + TRACK_HEIGHT, w, RULER_HEIGHT + TRACK_HEIGHT);

        // 3. Ruler
        g2.setColor(RULER_BG);
        g2.fillRect(SIDEBAR_WIDTH, 0, w - SIDEBAR_WIDTH, RULER_HEIGHT);
        g2.setColor(ACCENT_LILAC);
        g2.setFont(new Font("Monospaced", Font.PLAIN, 11));

        long dur = clip.getDurationFrames();
        long step = Math.max(1, dur / 5);
        for (long f = 0; f <= dur; f += step) {
            int x = clipFrameToX(f);
            g2.setColor(new Color(100, 100, 100));
            g2.drawLine(x, RULER_HEIGHT - 8, x, RULER_HEIGHT);
            g2.setColor(ACCENT_LILAC);
            g2.drawString(formatTC(f), x + 4, 15);
        }

        // 4. Sidebar Labels
        g2.setColor(ACCENT_LILAC);
        g2.setFont(new Font("Dialog", Font.BOLD, 12));
        g2.drawString("Posición", 10, RULER_HEIGHT + 16);

        g2.setColor(Color.WHITE);
        g2.drawString(clip.getMask().isEnabled() ? "[x] Máscara" : "[ ] Máscara", 10, RULER_HEIGHT + TRACK_HEIGHT + 16);

        // 5. Drawing Keyframe Line (Position)
        synchronized (clip.getTimeKeyframes()) {
            clip.getTimeKeyframes().sort(java.util.Comparator.comparingLong(TimelineKeyframe::getClipFrame));
        }
        g2.setColor(new Color(80, 80, 80));
        g2.drawLine(SIDEBAR_WIDTH, RULER_HEIGHT + TRACK_HEIGHT / 2, w, RULER_HEIGHT + TRACK_HEIGHT / 2);

        // Drawing Keyframe Line (Mask) - Mock representation
        g2.setColor(new Color(60, 60, 60));
        g2.drawLine(SIDEBAR_WIDTH, RULER_HEIGHT + TRACK_HEIGHT + TRACK_HEIGHT / 2, w,
                RULER_HEIGHT + TRACK_HEIGHT + TRACK_HEIGHT / 2);

        // 6. Diamonds
        for (TimelineKeyframe k : clip.getTimeKeyframes()) {
            int x = clipFrameToX(k.getClipFrame());
            int ky = RULER_HEIGHT + (TRACK_HEIGHT / 2);
            drawDiamond(g2, x, ky, k == selectedKeyframe);
        }

        // 7. Playhead
        int px = clipFrameToX(localPlayheadFrame);
        drawPlayhead(g2, px);

        // 8. Toolbar
        drawToolbar(g2, w, h);
    }

    private void drawDiamond(Graphics2D g2, int x, int ky, boolean selected) {
        int size = 7;
        Polygon d = new Polygon();
        d.addPoint(x, ky - size);
        d.addPoint(x + size, ky);
        d.addPoint(x, ky + size);
        d.addPoint(x - size, ky);

        g2.setColor(Color.decode("#999999"));
        g2.fill(d);
        g2.setColor(selected ? Color.WHITE : Color.decode("#333333"));
        g2.draw(d);
        if (selected) {
            g2.setColor(Color.BLACK);
            g2.fillRect(x - 1, ky - 1, 2, 2);
        }
    }

    private void drawPlayhead(Graphics2D g2, int px) {
        g2.setColor(Color.WHITE);
        Polygon p = new Polygon();
        p.addPoint(px - 6, 0);
        p.addPoint(px + 6, 0);
        p.addPoint(px + 6, RULER_HEIGHT - 8);
        p.addPoint(px, RULER_HEIGHT);
        p.addPoint(px - 6, RULER_HEIGHT - 8);
        g2.fill(p);

        g2.setColor(ACCENT_PURPLE);
        g2.drawLine(px, RULER_HEIGHT, px, getHeight() - TOOLBAR_HEIGHT);
    }

    private void drawToolbar(Graphics2D g2, int w, int h) {
        int ty = h - TOOLBAR_HEIGHT;
        g2.setColor(BG_COLOR_DARK);
        g2.fillRect(0, ty, w, TOOLBAR_HEIGHT);
        g2.setColor(Color.BLACK);
        g2.drawLine(0, ty, w, ty);

        int iconX = 60;
        int iconY = ty + 15;
        g2.setColor(ICON_COLOR);
        g2.fillRect(20, iconY, 12, 12); // Stop

        iconX = 60;
        g2.drawString("◀", iconX, iconY + 10);
        iconX += 40;
        g2.drawString("▶", iconX, iconY + 10);
        iconX += 40;
        g2.drawString("◆+", iconX, iconY + 10);
        iconX += 40;
        g2.drawString("◆x", iconX, iconY + 10);

        g2.setColor(new Color(200, 150, 50));
        g2.setFont(new Font("Monospaced", Font.BOLD, 14));
        g2.drawString(formatTC(localPlayheadFrame), w - 120, iconY + 12);
    }
}
