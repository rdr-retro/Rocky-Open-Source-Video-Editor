package rocky.ui.properties;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.awt.geom.AffineTransform;
import java.awt.geom.Path2D;
import java.awt.geom.Point2D;
import java.util.List;
import rocky.core.model.TimelineClip;
import rocky.core.model.TimelineKeyframe;
import rocky.core.model.ClipTransform;
import rocky.core.logic.TemporalMath;
import rocky.core.media.MediaPool;

/**
 * A canvas to visualize and manipulate the clip's transform.
 */
public class VisualCanvas extends JPanel {
    private final TimelineClip clip;
    private final MediaPool pool;
    private double zoom = 1.0;
    private Point lastMousePos;
    private Point2D initialMouseWorldPos;
    private double initialScaleX;
    private double initialScaleY;
    private ToolsSidebar.Tool currentTool = ToolsSidebar.Tool.SELECT;
    private rocky.core.media.MaskAnchor hoveredAnchor = null;
    private rocky.core.media.MaskAnchor selectedAnchor = null;

    // Transform interaction state
    private enum Action {
        NONE, MOVING, RESIZING, ROTATING
    }

    private Action currentAction = Action.NONE;
    private int resizeHandle = -1; // 0-7
    private double lastRotationAngle;
    private long localPlayheadFrame = 0;
    private ClipTransform initialTransformSnapshot;
    private final rocky.core.persistence.HistoryManager historyManager;
    private rocky.ui.timeline.TimelinePanel mainTimeline;
    private rocky.ui.timeline.ProjectProperties projectProps;

    public void setContext(rocky.ui.timeline.TimelinePanel timeline, rocky.ui.timeline.ProjectProperties props) {
        this.mainTimeline = timeline;
        this.projectProps = props;
    }

    public VisualCanvas(TimelineClip clip, MediaPool pool, rocky.core.persistence.HistoryManager historyManager) {
        this.clip = clip;
        this.pool = pool;
        this.historyManager = historyManager;
        setBackground(Color.decode("#1a1a1a"));

        MouseAdapter ma = new MouseAdapter() {
            @Override
            public void mousePressed(MouseEvent e) {
                if (historyManager != null) {
                    historyManager.pushState(mainTimeline, projectProps, pool);
                }
                lastMousePos = e.getPoint();
                Point2D p = inverseTransform(e.getPoint());

                // Initialize state for accurate dragging
                initialMouseWorldPos = p;
                initialTransformSnapshot = new ClipTransform(clip.getTransform());
                initialScaleX = clip.getTransform().getScaleX();
                initialScaleY = clip.getTransform().getScaleY();

                if (currentTool == ToolsSidebar.Tool.EDIT) { // Pen tool / Masking
                    if (hoveredAnchor != null && clip.getMask().getAnchors().indexOf(hoveredAnchor) == 0
                            && clip.getMask().getAnchors().size() > 2) {
                        clip.getMask().setClosed(true);
                    } else {
                        clip.getMask().addAnchor(p.getX(), p.getY());
                    }
                } else if (currentTool == ToolsSidebar.Tool.SELECT) {
                    // Check handles first
                    resizeHandle = findResizeHandleAt(e.getPoint());
                    if (resizeHandle != -1) {
                        currentAction = Action.RESIZING;
                    } else if (isInsideBox(e.getPoint())) {
                        currentAction = Action.MOVING;
                    } else if (isRotationArea(e.getPoint())) {
                        currentAction = Action.ROTATING;
                        lastRotationAngle = Math.toDegrees(Math.atan2(p.getY() - clip.getTransform().getY(),
                                p.getX() - clip.getTransform().getX()));
                    } else {
                        selectedAnchor = findAnchorAt(e.getPoint());
                        if (selectedAnchor == null)
                            currentAction = Action.NONE;
                    }
                }
                repaint();
            }

            @Override
            public void mouseWheelMoved(MouseWheelEvent e) {
                if (e.getWheelRotation() < 0)
                    zoom *= 1.1;
                else
                    zoom /= 1.1;
                repaint();
            }

            @Override
            public void mouseDragged(MouseEvent e) {
                Point2D p = inverseTransform(e.getPoint());
                double dx = p.getX() - inverseTransform(lastMousePos).getX();
                double dy = p.getY() - inverseTransform(lastMousePos).getY();

                if (SwingUtilities.isMiddleMouseButton(e)) {
                    // Pan could be implemented here
                } else if (currentAction == Action.MOVING) {
                    clip.getTransform().setX(clip.getTransform().getX() + dx);
                    clip.getTransform().setY(clip.getTransform().getY() + dy);
                } else if (currentAction == Action.ROTATING) {
                    double currentAngle = Math.toDegrees(Math.atan2(p.getY() - clip.getTransform().getY(),
                            p.getX() - clip.getTransform().getX()));

                    double delta = currentAngle - lastRotationAngle;

                    // Normalize delta to handle wrap-around (-180 to 180 boundary)
                    if (delta < -180)
                        delta += 360;
                    if (delta > 180)
                        delta -= 360;

                    clip.getTransform().setRotation(clip.getTransform().getRotation() + delta);
                    lastRotationAngle = currentAngle;
                } else if (currentAction == Action.RESIZING) {
                    double totalDx = p.getX() - initialMouseWorldPos.getX();
                    double totalDy = p.getY() - initialMouseWorldPos.getY();
                    handleResizing(totalDx, totalDy, e.isShiftDown());
                } else if (selectedAnchor != null) {
                    selectedAnchor.setX(p.getX());
                    selectedAnchor.setY(p.getY());
                }

                lastMousePos = e.getPoint();
                updateTransform();
            }

            @Override
            public void mouseMoved(MouseEvent e) {
                hoveredAnchor = findAnchorAt(e.getPoint());
                repaint();
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                selectedAnchor = null;
                currentAction = Action.NONE;
                resizeHandle = -1;
            }
        };
        addMouseListener(ma);
        addMouseMotionListener(ma);
        addMouseWheelListener(ma);
    }

    public void setCurrentTool(ToolsSidebar.Tool tool) {
        this.currentTool = tool;
        repaint();
    }

    public void setPlayheadFrame(long frame) {
        this.localPlayheadFrame = frame;
        repaint();
    }

    private void updateTransform() {
        // AUTO-KEYFRAME LOGIC
        // If there are NO keyframes yet:
        if (clip.getTimeKeyframes().isEmpty()) {
            // Case A: We are at Start (Frame 0) -> Apply GLOBAL change (no keyframes needed
            // yet)
            if (localPlayheadFrame == 0) {
                firePropertyChange("transform", null, clip.getTransform());
                repaint();
                return;
            }
            // Case B: We are NOT at Start -> User wants to animate FROM start TO here
            else {
                // 1. Create Keyframe at 0 with the INITIAL state (before this drag)
                // This preserves the static look up until this point.
                ClipTransform startT = (initialTransformSnapshot != null) ? initialTransformSnapshot
                        : new ClipTransform();
                clip.addKeyframe(new TimelineKeyframe(0, 0, new ClipTransform(startT)));

                // 2. Create Keyframe at current frame with NEW state will be handled by
                // "existing" logic below
                // (We just added one, so the check below will pass)
            }
        }

        // Auto-Keying Logic: Update existing or create new at current frame
        TimelineKeyframe existing = null;
        synchronized (clip.getTimeKeyframes()) {
            for (TimelineKeyframe k : clip.getTimeKeyframes()) {
                if (k.getClipFrame() == localPlayheadFrame) {
                    existing = k;
                    break;
                }
            }
        }

        if (existing != null) {
            existing.setTransform(new ClipTransform(clip.getTransform()));
        } else {
            // New keyframe at this position
            clip.addKeyframe(new TimelineKeyframe(
                    localPlayheadFrame, localPlayheadFrame, new ClipTransform(clip.getTransform())));
        }

        firePropertyChange("transform", null, clip.getTransform());
        repaint();
    }

    private rocky.core.media.MaskAnchor findAnchorAt(Point p) {
        for (rocky.core.media.MaskAnchor a : clip.getMask().getAnchors()) {
            Point ap = transformPoint(a.getX(), a.getY());
            if (p.distance(ap) < 8)
                return a;
        }
        return null;
    }

    private Point transformPoint(double x, double y) {
        int w = getWidth();
        int h = getHeight();
        int tx = (int) (w / 2 + x * zoom);
        int ty = (int) (h / 2 + y * zoom);
        return new Point(tx, ty);
    }

    private Point2D.Double inverseTransform(Point p) {
        int w = getWidth();
        int h = getHeight();
        double ix = (p.x - w / 2.0) / zoom;
        double iy = (p.y - h / 2.0) / zoom;
        return new Point2D.Double(ix, iy);
    }

    private int findResizeHandleAt(Point mouseP) {
        ClipTransform ct = clip.getTransform();
        double w = 300 * ct.getScaleX(); // Base width 300
        double h = 200 * ct.getScaleY(); // Base height 200

        Point[] handles = getHandlePoints(ct, w, h);
        for (int i = 0; i < handles.length; i++) {
            if (mouseP.distance(handles[i]) < 6)
                return i;
        }
        return -1;
    }

    private boolean isInsideBox(Point mouseP) {
        Point2D p = inverseTransform(mouseP);
        ClipTransform ct = clip.getTransform();

        // Rotate point back to test against axis-aligned box
        double rx = p.getX() - ct.getX();
        double ry = p.getY() - ct.getY();
        double angle = Math.toRadians(-ct.getRotation());
        double tx = rx * Math.cos(angle) - ry * Math.sin(angle);
        double ty = rx * Math.sin(angle) + ry * Math.cos(angle);

        double halfW = (300 * ct.getScaleX()) / 2;
        double halfH = (200 * ct.getScaleY()) / 2;

        return tx >= -halfW && tx <= halfW && ty >= -halfH && ty <= halfH;
    }

    private boolean isRotationArea(Point mouseP) {
        Point2D p = inverseTransform(mouseP);
        ClipTransform ct = clip.getTransform();
        double dist = p.distance(ct.getX(), ct.getY());
        double boxDiagonal = Math.sqrt(Math.pow(300 * ct.getScaleX(), 2) + Math.pow(200 * ct.getScaleY(), 2)) / 2;
        return dist > boxDiagonal && dist < boxDiagonal + 50;
    }

    private Point[] getHandlePoints(ClipTransform ct, double w, double h) {
        Point[] pts = new Point[8];
        double[] hw = { -w / 2, 0, w / 2, w / 2, w / 2, 0, -w / 2, -w / 2 };
        double[] hh = { -h / 2, -h / 2, -h / 2, 0, h / 2, h / 2, h / 2, 0 };

        double angle = Math.toRadians(ct.getRotation());
        for (int i = 0; i < 8; i++) {
            double tx = hw[i] * Math.cos(angle) - hh[i] * Math.sin(angle);
            double ty = hw[i] * Math.sin(angle) + hh[i] * Math.cos(angle);
            pts[i] = transformPoint(ct.getX() + tx, ct.getY() + ty);
        }
        return pts;
    }

    private void handleResizing(double totalDx, double totalDy, boolean isShift) {
        // Base dimensions for scale 1.0 (used in findResizeHandleAt)
        double baseHalfW = 150.0;
        double baseHalfH = 100.0;

        // Calculate raw scale change factors based on mouse movement
        double factorX = totalDx / baseHalfW;
        double factorY = totalDy / baseHalfH;

        // We will calculate target scales relative to the INITIAL state
        double targetScaleX = initialScaleX;
        double targetScaleY = initialScaleY;

        // Apply directionality based on handle
        // 0=TL, 1=TC, 2=TR, 3=RC, 4=BR, 5=BC, 6=BL, 7=LC
        switch (resizeHandle) {
            case 0: // Top-Left
                targetScaleX -= factorX;
                targetScaleY -= factorY;
                break;
            case 1: // Top
                targetScaleY -= factorY;
                break;
            case 2: // Top-Right
                targetScaleX += factorX;
                targetScaleY -= factorY;
                break;
            case 3: // Right
                targetScaleX += factorX;
                break;
            case 4: // Bottom-Right
                targetScaleX += factorX;
                targetScaleY += factorY;
                break;
            case 5: // Bottom
                targetScaleY += factorY;
                break;
            case 6: // Bottom-Left
                targetScaleX -= factorX;
                targetScaleY += factorY;
                break;
            case 7: // Left
                targetScaleX -= factorX;
                break;
        }

        // Apply Proportional Logic if it's a CORNER handle and SHIFT is NOT held
        boolean isCorner = (resizeHandle == 0 || resizeHandle == 2 || resizeHandle == 4 || resizeHandle == 6);
        if (isCorner && !isShift) {
            double initialRatio = initialScaleX / initialScaleY;

            // Determine dominant change to drive aspect ratio
            // We use the magnitude of change relative to the initial size to decide
            // "intent"
            double deltaX = Math.abs(targetScaleX - initialScaleX);
            double deltaY = Math.abs(targetScaleY - initialScaleY);

            // Normalizing delta by aspect ratio to compare "visual" distance
            // If aspect is 2:1 (X=2, Y=1), a change of 0.2 in X is "less" impactful than
            // 0.2 in Y?
            // Simple approach: Use the larger relative change
            // Or simpler: Use the MAX scale factor to drive the other

            if (deltaX > deltaY * initialRatio) {
                // X is dominant
                targetScaleY = targetScaleX / initialRatio;
            } else {
                // Y is dominant
                targetScaleX = targetScaleY * initialRatio;
            }
        }

        // Safety clamps (prevent flipping/zero for now if desired, though standard
        // tools often allow flipping)
        // Let's keep a tiny minimum to avoid errors
        if (Math.abs(targetScaleX) < 0.01)
            targetScaleX = 0.01 * Math.signum(targetScaleX);
        if (Math.abs(targetScaleY) < 0.01)
            targetScaleY = 0.01 * Math.signum(targetScaleY);

        clip.getTransform().setScaleX(targetScaleX);
        clip.getTransform().setScaleY(targetScaleY);
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g;
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int winW = getWidth();
        int winH = getHeight();

        // 1. Draw Grid
        drawGrid(g2, winW, winH);

        // 2. Transformed drawing
        AffineTransform old = g2.getTransform();
        g2.translate(winW / 2, winH / 2);
        g2.scale(zoom, zoom);

        // Draw Workspace circle
        g2.setColor(new Color(200, 200, 200, 100));
        float[] dash = { 4f / (float) zoom, 4f / (float) zoom };
        g2.setStroke(new BasicStroke((float) (1 / zoom), BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 10, dash, 0));
        g2.drawOval(-200, -200, 400, 400);

        // 3. Draw Clip Bounding Box (Sony Vegas Style)
        drawTransformBox(g2);

        // 4. Draw Mask Path
        drawMask(g2);

        g2.setTransform(old);

        // 5. Draw Handles and Anchors (Size independent)
        drawHandles(g2);
        drawAnchors(g2);
    }

    private void drawTransformBox(Graphics2D g2) {
        ClipTransform ct = clip.getTransform();
        AffineTransform boxAt = new AffineTransform();
        boxAt.translate(ct.getX(), ct.getY());
        boxAt.rotate(Math.toRadians(ct.getRotation()));

        AffineTransform oldAt = g2.getTransform();
        g2.transform(boxAt);

        double w = 300 * ct.getScaleX();
        double h = 200 * ct.getScaleY();

        // --- LIVE PREVIEW (Actual Image) ---
        if (pool != null) {
            rocky.core.media.MediaSource source = pool.getSource(clip.getMediaSourceId());
            if (source != null) {
                // For preview, use the actual source frame at current playhead
                long sourceFrame = TemporalMath.getSourceFrameAt(clip, localPlayheadFrame);
                BufferedImage img = source.getFrame(sourceFrame);
                if (img != null) {
                    g2.drawImage(img, (int) (-w / 2), (int) (-h / 2), (int) w, (int) h, null);
                }
            }
        }

        g2.setColor(Color.WHITE);
        float[] dash = { 4f / (float) zoom, 4f / (float) zoom };
        g2.setStroke(new BasicStroke((float) (1.5 / zoom), BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 10, dash, 0));
        g2.drawRect((int) (-w / 2), (int) (-h / 2), (int) w, (int) h);

        // Center cross
        g2.drawLine(-10, 0, 10, 0);
        g2.drawLine(0, -10, 0, 10);
        g2.drawOval(-4, -4, 8, 8);

        g2.setTransform(oldAt);
    }

    private void drawHandles(Graphics2D g2) {
        if (currentTool != ToolsSidebar.Tool.SELECT)
            return;
        ClipTransform ct = clip.getTransform();
        double w = 300 * ct.getScaleX();
        double h = 200 * ct.getScaleY();
        Point[] pts = getHandlePoints(ct, w, h);

        g2.setColor(Color.WHITE);
        for (int i = 0; i < pts.length; i++) {
            g2.fillRect(pts[i].x - 3, pts[i].y - 3, 6, 6);
            g2.setColor(Color.BLACK);
            g2.drawRect(pts[i].x - 3, pts[i].y - 3, 6, 6);
            g2.setColor(Color.WHITE);
        }
    }

    private void drawMask(Graphics2D g2) {
        List<rocky.core.media.MaskAnchor> anchors = clip.getMask().getAnchors();
        if (anchors.isEmpty())
            return;

        g2.setColor(Color.WHITE);
        float[] dash = { 4f / (float) zoom, 4f / (float) zoom };
        g2.setStroke(new BasicStroke((float) (1.5 / zoom), BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 10, dash, 0));

        Path2D path = new Path2D.Double();
        path.moveTo(anchors.get(0).getX(), anchors.get(0).getY());
        for (int i = 1; i < anchors.size(); i++) {
            path.lineTo(anchors.get(i).getX(), anchors.get(i).getY());
        }
        if (clip.getMask().isClosed()) {
            path.closePath();
        }
        g2.draw(path);
    }

    private void drawAnchors(Graphics2D g2) {
        for (rocky.core.media.MaskAnchor a : clip.getMask().getAnchors()) {
            Point p = transformPoint(a.getX(), a.getY());
            g2.setColor(Color.WHITE);
            int size = (a == hoveredAnchor) ? 8 : 6;
            g2.fillRect(p.x - size / 2, p.y - size / 2, size, size);
            g2.setColor(Color.BLACK);
            g2.drawRect(p.x - size / 2, p.y - size / 2, size, size);
        }
    }

    private void drawGrid(Graphics2D g2, int w, int h) {
        g2.setColor(new Color(60, 60, 60));
        g2.setStroke(new BasicStroke(1));

        int step = (int) (20 * zoom);
        if (step < 5)
            step = 5;

        for (int x = 0; x < w; x += step)
            g2.drawLine(x, 0, x, h);
        for (int y = 0; y < h; y += step)
            g2.drawLine(0, y, w, y);

        // Draw dots (like in image)
        g2.setColor(new Color(150, 150, 150));
        for (int x = 0; x < w; x += 40) {
            for (int y = 0; y < h; y += 40) {
                g2.fillRect(x - 1, y - 1, 2, 2);
            }
        }
    }
}
