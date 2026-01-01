package rocky.core.engine;

import rocky.ui.timeline.TimelineClip;
import rocky.ui.timeline.TimelinePanel;
import rocky.core.media.MediaPool;
import rocky.core.media.MediaSource;
import java.util.List;
import java.awt.image.BufferedImage;

/**
 * The logic that determines what to show on the visor based on playhead
 * position.
 */
public class FrameServer {
    private TimelinePanel timeline;
    private MediaPool pool;
    private rocky.ui.viewer.VisualizerPanel visualizer;
    private rocky.ui.timeline.ProjectProperties properties;
    private final java.util.concurrent.ExecutorService executor = java.util.concurrent.Executors
            .newSingleThreadExecutor();
    private long lastSubmittedFrame = -1;

    public FrameServer(TimelinePanel timeline, MediaPool pool, rocky.ui.viewer.VisualizerPanel visualizer) {
        this.timeline = timeline;
        this.pool = pool;
        this.visualizer = visualizer;
    }

    public void setProperties(rocky.ui.timeline.ProjectProperties props) {
        this.properties = props;
    }

    public TimelinePanel getTimeline() {
        return timeline;
    }

    public MediaPool getMediaPool() {
        return pool;
    }

    public void processFrame(double timeInSeconds) {
        processFrame(timeInSeconds, false);
    }

    public void processFrame(double timeInSeconds, boolean force) {
        double fps = (properties != null) ? properties.getFPS() : 30.0;
        long targetFrame = (long) (timeInSeconds * fps); 

        if (!force && targetFrame == lastSubmittedFrame)
            return;
        lastSubmittedFrame = targetFrame;

        executor.submit(() -> {
            BufferedImage rendered = getFrameAt(targetFrame, false);
            if (rendered == null) return;

            // Clone to avoid tearing if the buffer is reused before paint
            BufferedImage finalImg = new BufferedImage(rendered.getWidth(), rendered.getHeight(), rendered.getType());
            java.awt.Graphics2D g2 = finalImg.createGraphics();
            g2.drawImage(rendered, 0, 0, null);
            g2.dispose();

            javax.swing.SwingUtilities.invokeLater(() -> {
                visualizer.updateFrame(finalImg);
            });
        });
    }

    private BufferedImage cachedCanvas;

    public BufferedImage getFrameAt(long targetFrame, boolean forceFullRes) {
        if (properties == null)
            return null;

        int canvasW = properties.getProjectWidth();
        int canvasH = properties.getProjectHeight();

        if (properties.isLowResPreview() && !forceFullRes) {
            canvasW = properties.getPreviewWidth();
            canvasH = properties.getPreviewHeight();
        }

        // --- Performance Optimization: Buffer Reuse ---
        if (cachedCanvas == null || cachedCanvas.getWidth() != canvasW || cachedCanvas.getHeight() != canvasH) {
            cachedCanvas = new BufferedImage(canvasW, canvasH, BufferedImage.TYPE_INT_ARGB);
        }
        
        BufferedImage canvas = cachedCanvas;
        java.awt.Graphics2D g2 = canvas.createGraphics();
        g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION,
                java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR);

        // Background
        g2.setColor(java.awt.Color.BLACK);
        g2.fillRect(0, 0, canvasW, canvasH);

        // Get clips active at this frame, sorted by track index (descending so lower
        // index draws last/on top)
        List<TimelineClip> allClips = timeline.getClips();
        java.util.List<TimelineClip> activeClips = new java.util.ArrayList<>();
        for (TimelineClip clip : allClips) {
            if (targetFrame >= clip.getStartFrame()
                    && targetFrame < (clip.getStartFrame() + clip.getDurationFrames())) {
                if (timeline.getTrackType(clip.getTrackIndex()) == rocky.ui.timeline.TrackControlPanel.TrackType.VIDEO) {
                    activeClips.add(clip);
                }
            }
        }
        activeClips.sort((a, b) -> Integer.compare(b.getTrackIndex(), a.getTrackIndex()));

        for (TimelineClip clip : activeClips) {
            MediaSource source = pool.getSource(clip.getMediaSourceId());
            if (source == null)
                continue;

            long frameInClip = targetFrame - clip.getStartFrame();
            long sourceFrame = clip.getSourceFrameAt(frameInClip);
            BufferedImage asset = source.getFrame(sourceFrame);
            if (asset == null)
                continue;

            drawAssetOnCanvas(g2, asset, clip, frameInClip, canvasW, canvasH);
        }

        g2.dispose();
        return canvas;
    }

    private void drawAssetOnCanvas(java.awt.Graphics2D g2, BufferedImage asset, TimelineClip clip, long frameInClip,
            int canvasW, int canvasH) {
        int assetW = asset.getWidth();
        int assetH = asset.getHeight();

        // 1. Uniform Scale to fit project if requested (Aspect Ratio preservation)
        double fitScale = Math.min((double) canvasW / assetW, (double) canvasH / assetH);

        // 2. Apply Custom Transform (Interpolated if keyframes exist)
        rocky.ui.timeline.ClipTransform transform = clip.getInterpolatedTransform(frameInClip);
        double finalScaleX = fitScale * transform.getScaleX();
        double finalScaleY = fitScale * transform.getScaleY();

        double renderW = assetW * finalScaleX;
        double renderH = assetH * finalScaleY;

        // Centering by default + user offset
        // User x=0, y=0 means centered in project
        double centerX = (canvasW / 2.0) + transform.getX();
        double centerY = (canvasH / 2.0) + transform.getY();

        java.awt.geom.AffineTransform at = new java.awt.geom.AffineTransform();
        at.translate(centerX, centerY);
        at.rotate(Math.toRadians(transform.getRotation()));
        at.scale(finalScaleX, finalScaleY);
        // Anchor point (default center of the image)
        at.translate(-assetW * transform.getAnchorX(), -assetH * transform.getAnchorY());

        float opacity = (float) clip.getOpacityAt(frameInClip);
        java.awt.Composite oldComp = g2.getComposite();
        if (opacity < 1.0f) {
            g2.setComposite(java.awt.AlphaComposite.getInstance(java.awt.AlphaComposite.SRC_OVER, Math.max(0.0f, opacity)));
        }

        g2.drawImage(asset, at, null);

        if (opacity < 1.0f) {
            g2.setComposite(oldComp);
        }
    }
}
