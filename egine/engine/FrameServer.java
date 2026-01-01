package egine.engine;

import b.timeline.TimelineClip;
import b.timeline.TimelinePanel;
import egine.media.MediaPool;
import egine.media.MediaSource;
import java.util.List;
import java.awt.image.BufferedImage;

/**
 * The logic that determines what to show on the visor based on playhead
 * position.
 */
public class FrameServer {
    private TimelinePanel timeline;
    private MediaPool pool;
    private a.visor.VisualizerPanel visualizer;
    private b.timeline.ProjectProperties properties;
    private final java.util.concurrent.ExecutorService executor = java.util.concurrent.Executors
            .newSingleThreadExecutor();
    private long lastSubmittedFrame = -1;

    public FrameServer(TimelinePanel timeline, MediaPool pool, a.visor.VisualizerPanel visualizer) {
        this.timeline = timeline;
        this.pool = pool;
        this.visualizer = visualizer;
    }

    public void setProperties(b.timeline.ProjectProperties props) {
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
        long targetFrame = (long) (timeInSeconds * 30); // Assuming 30 FPS

        if (!force && targetFrame == lastSubmittedFrame)
            return;
        lastSubmittedFrame = targetFrame;

        executor.submit(() -> {
            BufferedImage canvas = getFrameAt(targetFrame);

            final BufferedImage finalImg = canvas;
            javax.swing.SwingUtilities.invokeLater(() -> {
                visualizer.updateFrame(finalImg);
            });
        });
    }

    public BufferedImage getFrameAt(long targetFrame) {
        if (properties == null)
            return null;

        int canvasW = properties.getProjectWidth();
        int canvasH = properties.getProjectHeight();

        if (properties.isLowResPreview()) {
            canvasW = properties.getPreviewWidth();
            canvasH = properties.getPreviewHeight();
        }

        BufferedImage canvas = new BufferedImage(canvasW, canvasH, BufferedImage.TYPE_INT_RGB);
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
                if (timeline.getTrackType(clip.getTrackIndex()) == b.timeline.TrackControlPanel.TrackType.VIDEO) {
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

            drawAssetOnCanvas(g2, asset, clip, canvasW, canvasH);
        }

        g2.dispose();
        return canvas;
    }

    private void drawAssetOnCanvas(java.awt.Graphics2D g2, BufferedImage asset, TimelineClip clip, int canvasW,
            int canvasH) {
        int assetW = asset.getWidth();
        int assetH = asset.getHeight();

        // 1. Uniform Scale to fit project if requested (Aspect Ratio preservation)
        double fitScale = Math.min((double) canvasW / assetW, (double) canvasH / assetH);

        // 2. Apply Custom Transform
        b.timeline.ClipTransform transform = clip.getTransform();
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

        g2.drawImage(asset, at, null);
    }
}
