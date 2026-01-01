package rocky.ui.timeline;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

public class TimelineRuler extends JPanel {
    private final int FPS = 30;
    
    // Reference to main timeline for shared state
    private TimelinePanel timeline;
    
    private final Color RULER_BG = Color.decode("#2d2d2d");
    private final Color TICK_COLOR = Color.decode("#808080");
    private final Color TEXT_COLOR = Color.decode("#b0b0b0");
    private final Color HOVER_CURSOR_COLOR = Color.decode("#d4d4d4");

    private int mouseX = -1;

    public TimelineRuler(TimelinePanel timeline) {
        this.timeline = timeline;
        setBackground(RULER_BG);
        setPreferredSize(new Dimension(0, 30)); // Fixed height
        
        MouseAdapter mouseHandler = new MouseAdapter() {
            @Override
            public void mouseMoved(MouseEvent e) {
                mouseX = e.getX();
                repaint();
                // Optional: Sync hover cursor in timeline panel?
            }
            
            @Override
            public void mouseExited(MouseEvent e) {
                mouseX = -1;
                repaint();
            }

            @Override
            public void mousePressed(MouseEvent e) {
                // Clicking ruler jumps playhead
                timeline.setPlayheadFromScreenX(e.getX());
                repaint();
            }

            @Override
            public void mouseDragged(MouseEvent e) {
                // Dragging in ruler scrubs playhead
                timeline.setPlayheadFromScreenX(e.getX());
                mouseX = e.getX();
                repaint();
            }
        };
        
        addMouseListener(mouseHandler);
        addMouseMotionListener(mouseHandler);
    }

    private String formatTimecode(long totalFrames) {
        // Delegate to timeline's blueline if possible or use local fallback
        // Since we refactored, let's just use the logic from TimelinePanel
        return timeline.formatTimecode(totalFrames);
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2d = (Graphics2D) g;
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int width = getWidth();
        int height = getHeight();

        // Background
        g2d.setColor(RULER_BG);
        g2d.fillRect(0, 0, width, height);
        
        // Ticks
        double pixelsPerSecond = timeline.getPixelsPerSecond();
        double visibleStartTime = timeline.getVisibleStartTime();
        
        // Calculate dynamic step based on text width
        String exampleText = "00:00:00;00";
        FontMetrics fm = g2d.getFontMetrics();
        int labelWidth = fm.stringWidth(exampleText);
        int minSpacing = labelWidth + 20; // Min spacing in pixels
        
        // Find smallest logical time interval that fits in minSpacing pixels
        // Candidates (seconds): 1 frame (1/30), 0.1, 0.5, 1, 2, 5, 10, 15, 30, 60 (1m), 120 (2m), 300 (5m), 600 (10m)...
        double[] candidates = { 
            1.0/FPS, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 
            60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0 
        };
        
        double step = candidates[candidates.length-1];
        for (double s : candidates) {
            if (s * pixelsPerSecond >= minSpacing) {
                step = s;
                break;
            }
        }
        
        double viewStartSec = visibleStartTime;
        double viewEndSec = timeline.screenToTime(width);
        
        // Align start to step
        double startTick = Math.floor(viewStartSec / step) * step;
        
        g2d.setColor(TICK_COLOR);
        g2d.setFont(new Font("SansSerif", Font.PLAIN, 10));

        // Safety cap to prevent infinite loops if something is wrong
        int maxTicks = 200; 
        int drawn = 0;

        for (double t = startTick; t < viewEndSec + step; t += step) {
             if (drawn++ > maxTicks) break;
             
            int tx = timeline.timeToScreen(t);
            
            if (tx < -50 || tx > width + 50) continue; // Culling
            
            // Major tick
            g2d.drawLine(tx, 15, tx, height);
            
            // Label
            long totalFrames = (long) Math.round(t * FPS);
            String timeStr = formatTimecode(totalFrames);
            g2d.setColor(TEXT_COLOR);
            g2d.drawString(timeStr, tx + 5, 25);
            g2d.setColor(TICK_COLOR);

            // Subticks (only if space permits)
            int subticks = 4; // default 4 subticks -> 5 divisions
            double subStep = step / (subticks + 1.0);
            
            if (subStep * pixelsPerSecond > 10) { 
               for (int i=1; i<=subticks; i++) {
                   int sx = timeline.timeToScreen(t + subStep*i);
                    // Standard height or smaller?
                   if (sx > tx && sx < width) {
                        g2d.drawLine(sx, 22, sx, height);
                   }
               }
            }
        }
        
        g2d.setColor(Color.BLACK);
        g2d.drawLine(0, height - 1, width, height - 1);
        
        // Draw Cursors
        
        // Hover (Triangle)
        if (mouseX >= 0) {
            g2d.setColor(HOVER_CURSOR_COLOR);
            int[] hx = {mouseX - 3, mouseX + 3, mouseX};
            int[] hy = {0, 0, 5};
            g2d.fillPolygon(hx, hy, 3);
        }
        
        // Playhead (Head)
        long playheadFrame = timeline.getPlayheadFrame();
        int playheadX = timeline.timeToScreen(playheadFrame / (double) FPS);
        
        if (playheadX >= -10 && playheadX <= width + 10) {
            g2d.setColor(timeline.getPlayheadColor());
            int[] px = {playheadX - 5, playheadX + 5, playheadX};
            int[] py = {0, 0, 15};
            g2d.fillPolygon(px, py, 3);
        }
    }
}
