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
            .newFixedThreadPool(Runtime.getRuntime().availableProcessors());
    private final java.util.concurrent.ConcurrentHashMap<Long, BufferedImage> frameCache = new java.util.concurrent.ConcurrentHashMap<>();
    private final int MAX_CACHE_SIZE = 60;
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

        // Sony-Vegas Style: Return cached frame immediately if available
        if (frameCache.containsKey(targetFrame)) {
            visualizer.updateFrame(frameCache.get(targetFrame));
            prefetchNextFrames(targetFrame, 15); // Pre-fetch 15 frames ahead
            return;
        }

        executor.submit(() -> {
            BufferedImage rendered = getFrameAt(targetFrame, false);
            if (rendered == null)
                return;

            // We put it in cache and notify visualizer
            frameCache.put(targetFrame, rendered);
            manageCacheSize(targetFrame);

            javax.swing.SwingUtilities.invokeLater(() -> {
                visualizer.updateFrame(rendered);
            });
            
            prefetchNextFrames(targetFrame, 15);
        });
    }

    private void prefetchNextFrames(long startFrame, int count) {
        for (int i = 1; i <= count; i++) {
            final long f = startFrame + i;
            if (!frameCache.containsKey(f)) {
                executor.submit(() -> {
                    if (frameCache.size() < MAX_CACHE_SIZE) {
                        BufferedImage prefetched = getFrameAt(f, false);
                        if (prefetched != null) {
                            frameCache.put(f, prefetched);
                        }
                    }
                });
            }
        }
    }

    private void manageCacheSize(long currentFrame) {
        if (frameCache.size() > MAX_CACHE_SIZE) {
            // Remove frames far away from current
            frameCache.keySet().removeIf(f -> Math.abs(f - currentFrame) > MAX_CACHE_SIZE / 2);
        }
    }

    private BufferedImage cloneImage(BufferedImage src) {
        BufferedImage dest = new BufferedImage(src.getWidth(), src.getHeight(), src.getType());
        java.awt.Graphics2D g = dest.createGraphics();
        g.drawImage(src, 0, 0, null);
        g.dispose();
        return dest;
    }


    public BufferedImage getFrameAt(long targetFrame, boolean forceFullRes) {
        if (properties == null)
            return null;

        int canvasW = properties.getProjectWidth();
        int canvasH = properties.getProjectHeight();

        if (properties.isLowResPreview() && !forceFullRes) {
            canvasW = properties.getPreviewWidth();
            canvasH = properties.getPreviewHeight();
        }

        BufferedImage canvas = new BufferedImage(canvasW, canvasH, BufferedImage.TYPE_INT_ARGB);
        java.awt.Graphics2D g2 = canvas.createGraphics();
        
        // Quality Presets
        String quality = properties.getPreviewQuality(); // Draft, Preview, Good, Best
        
        if (quality.equals("Best") || quality.equals("Good")) {
            g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_BICUBIC);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_RENDERING, java.awt.RenderingHints.VALUE_RENDER_QUALITY);
        } else {
            g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_OFF);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_RENDERING, java.awt.RenderingHints.VALUE_RENDER_SPEED);
        }

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
        
        // --- ACES COLOR MANAGEMENT ---
        if (properties.isAcesEnabled()) {
            ColorManagement.applyAces(canvas);
        }
        
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
