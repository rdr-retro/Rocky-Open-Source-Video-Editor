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
    private rocky.core.model.TimelineModel model;
    private MediaPool pool;
    private rocky.ui.viewer.VisualizerPanel visualizer;
    private rocky.ui.timeline.ProjectProperties properties;
    private final rocky.core.diagnostics.PerformanceMonitor monitor;
    private final java.util.concurrent.ThreadPoolExecutor executor;
    private final java.util.concurrent.ConcurrentHashMap<Long, BufferedImage> frameCache = new java.util.concurrent.ConcurrentHashMap<>();
    private final java.util.concurrent.ConcurrentLinkedQueue<BufferedImage> bufferPool = new java.util.concurrent.ConcurrentLinkedQueue<>();
    private final java.util.concurrent.atomic.AtomicLong latestTargetFrame = new java.util.concurrent.atomic.AtomicLong(
            -1);
    private BufferedImage currentVisibleBuffer = null;
    private long lastRequestTime = 0;
    private double currentScrubbingVelocity = 0; // frames per ms
    private final int MAX_POOL_SIZE = 10;

    // Vegas Adaptive Quality

    public FrameServer(rocky.core.model.TimelineModel model, MediaPool pool, rocky.ui.viewer.VisualizerPanel visualizer) {
        this.model = model;
        this.pool = pool;
        this.visualizer = visualizer;
        this.monitor = new rocky.core.diagnostics.PerformanceMonitor();

        int cores = Runtime.getRuntime().availableProcessors();
        this.executor = new java.util.concurrent.ThreadPoolExecutor(
                cores, cores, 0L, java.util.concurrent.TimeUnit.MILLISECONDS,
                new java.util.concurrent.PriorityBlockingQueue<Runnable>());
    }

    private int getRamCacheLimitFrames() {
        if (properties == null)
            return 60;
        int mbLimit = 512; // Fixed limit since slider is removed
        int width = properties.getPreviewWidth();
        int height = properties.getPreviewHeight();
        // Bytes per frame = width * height * 4 (RGBA)
        long bytesPerFrame = (long) width * height * 4;
        if (bytesPerFrame == 0)
            return 60;

        long totalBytes = (long) mbLimit * 1024 * 1024;
        return (int) (totalBytes / bytesPerFrame);
    }

    private class RenderTask implements Runnable, Comparable<RenderTask> {
        private final long frame;
        private final boolean isPrefetch;
        private final long requestOrder;
        private final long taskRevision;
        private static final java.util.concurrent.atomic.AtomicLong orderSource = new java.util.concurrent.atomic.AtomicLong(
                0);

        public RenderTask(long frame, boolean isPrefetch, long taskRevision) {
            this.frame = frame;
            this.isPrefetch = isPrefetch;
            this.taskRevision = taskRevision;
            this.requestOrder = orderSource.getAndIncrement();
        }

        @Override
        public void run() {
            // 1. Revision Check
            if (model.getLayoutRevision() > taskRevision) {
                return;
            }

            if (latestTargetFrame.get() != -1 && !isPrefetch) {
                if (latestTargetFrame.get() != frame)
                    return;
            }

            if (!isPrefetch) {
                monitor.startFrame();
                monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.SEEK_START);
            }

            // ... checks ...

            // 2. Double-check synchronization
            BufferedImage rendered;
            try {
                // Time handled inside getFrameAt via marks
                rendered = getFrameAt(frame, false);
            } catch (Exception e) {
                e.printStackTrace();
                return;
            }

            // ... checks ...

            if (!isPrefetch) {
                 monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_START); // Only UI update remains
                javax.swing.SwingUtilities.invokeLater(() -> {
                    // Recycle the OLD visible buffer now that it's being replaced
                    if (currentVisibleBuffer != null && currentVisibleBuffer != rendered) {
                        returnCanvasToPool(currentVisibleBuffer);
                    }
                    currentVisibleBuffer = rendered;
                    visualizer.updateFrame(rendered);
                    monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_END);
                    monitor.endFrame();
                });
            }

            if (isPrefetch && Math.abs(latestTargetFrame.get() - frame) > 20)
                return;

            if (rendered == null)
                return;

            // 3. Final Revision Check before UI Update
            if (model.getLayoutRevision() > taskRevision) {
                returnCanvasToPool(rendered);
                return;
            }

            // Relaxed check: Allow 1 frame drift to prevent micro-stuttering
            // If the UI is slightly ahead (e.g. 102 vs 101), showing 101 is better than
            // showing nothing.
            if (!isPrefetch && Math.abs(latestTargetFrame.get() - frame) > 1) {
                returnCanvasToPool(rendered);
                return;
            }

            frameCache.put(frame, rendered);
            manageCacheSize(frame);

            if (!isPrefetch) {
                javax.swing.SwingUtilities.invokeLater(() -> {
                    // Recycle the OLD visible buffer now that it's being replaced
                    if (currentVisibleBuffer != null && currentVisibleBuffer != rendered) {
                        returnCanvasToPool(currentVisibleBuffer);
                    }
                    currentVisibleBuffer = rendered;
                    visualizer.updateFrame(rendered);
                });
            }
        }

        @Override
        public int compareTo(RenderTask other) {
            long target = latestTargetFrame.get();
            long distA = Math.abs(this.frame - target);
            long distB = Math.abs(other.frame - target);

            if (distA != distB)
                return Long.compare(distA, distB);
            if (this.isPrefetch != other.isPrefetch)
                return this.isPrefetch ? 1 : -1;
            return Long.compare(other.requestOrder, this.requestOrder); // Newer first
        }
    }

    public rocky.ui.timeline.ProjectProperties getProperties() {
        return properties;
    }

    public void setProperties(rocky.ui.timeline.ProjectProperties props) {
        this.properties = props;
    }

    public rocky.core.model.TimelineModel getModel() {
        return model;
    }

    public MediaPool getMediaPool() {
        return pool;
    }

    /**
     * Invalidates the frame cache. Should be called when timeline structure changes
     * (clips moved, added, or deleted) to prevent ghost images.
     */
    public void invalidateCache() {
        // Clear the current visible frame immediately to prevent ghost images
        long currentFrame = latestTargetFrame.get();
        if (currentFrame >= 0) {
            BufferedImage removed = frameCache.remove(currentFrame);
            if (removed != null && removed != currentVisibleBuffer) {
                returnCanvasToPool(removed);
            }
        }

        // Clear the entire cache for a clean slate
        for (BufferedImage img : frameCache.values()) {
            if (img != null && img != currentVisibleBuffer) {
                returnCanvasToPool(img);
            }
        }
        frameCache.clear();

        // Force the current visible buffer to be black/empty to avoid showing stale
        // content
        if (currentVisibleBuffer != null) {
            java.awt.Graphics2D g = currentVisibleBuffer.createGraphics();
            g.setColor(java.awt.Color.BLACK);
            g.fillRect(0, 0, currentVisibleBuffer.getWidth(), currentVisibleBuffer.getHeight());
            g.dispose();
        }
    }

    public void processFrame(double timeInSeconds) {
        processFrame(timeInSeconds, false);
    }

    public void processFrame(double timeInSeconds, boolean force) {
        double fps = (properties != null) ? properties.getFPS() : 30.0;
        long targetFrame = Math.round(timeInSeconds * fps);

        if (force) {
            BufferedImage removed = frameCache.remove(targetFrame);
            if (removed != null)
                returnCanvasToPool(removed);
        } else if (frameCache.containsKey(targetFrame)) {
            visualizer.updateFrame(frameCache.get(targetFrame));
            prefetchFrames(targetFrame);
            return;
        }

        long now = System.currentTimeMillis();
        if (lastRequestTime > 0) {
            long dt = now - lastRequestTime;
            if (dt > 0) {
                double vel = (double) Math.abs(targetFrame - latestTargetFrame.get()) / dt;
                currentScrubbingVelocity = 0.8 * currentScrubbingVelocity + 0.2 * vel;
            }
        }
        lastRequestTime = now;
        latestTargetFrame.set(targetFrame);

        executor.execute(new RenderTask(targetFrame, false, model.getLayoutRevision()));
        
        // --- SMART LOOK-AHEAD ---
        // Only prefetch if scrubbing is slow or we are playing (vel approx 0 or steady 1x)
        if (currentScrubbingVelocity < 1.0) {
            prefetchFrames(targetFrame);
        }
    }

    private void prefetchFrames(long centerFrame) {
        int radius = 10;
        // Prefetch forward
        int enqueued = 0;
        for (int i = 1; i <= radius; i++) {
            final long f = centerFrame + i;
            if (!frameCache.containsKey(f)) {
                executor.execute(new RenderTask(f, true, model.getLayoutRevision()));
            } else {
                enqueued++;
            }
        }
        monitor.updateBufferSize(frameCache.size());
        // Prefetch backward (useful for scrubbing left)
        for (int i = 1; i <= radius / 2; i++) {
            final long f = centerFrame - i;
            if (f >= 0 && !frameCache.containsKey(f)) {
                executor.execute(new RenderTask(f, true, model.getLayoutRevision()));
            }
        }
    }


    private void manageCacheSize(long currentFrame) {
        int maxFrames = getRamCacheLimitFrames();
        if (frameCache.size() > maxFrames) {
            // Remove frames far away from current
            java.util.Iterator<java.util.Map.Entry<Long, BufferedImage>> it = frameCache.entrySet().iterator();
            while (it.hasNext()) {
                java.util.Map.Entry<Long, BufferedImage> entry = it.next();
                if (Math.abs(entry.getKey() - currentFrame) > maxFrames) {
                    // DON'T recycle if it's currently on screen!
                    if (entry.getValue() != currentVisibleBuffer) {
                        returnCanvasToPool(entry.getValue());
                    }
                    it.remove();
                }
            }
        }
    }

    private BufferedImage getCanvasFromPool(int w, int h) {
        BufferedImage img = bufferPool.poll();
        if (img == null || img.getWidth() != w || img.getHeight() != h) {
            return new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB_PRE);
        }
        return img;
    }

    private void returnCanvasToPool(BufferedImage img) {
        if (bufferPool.size() < MAX_POOL_SIZE) {
            bufferPool.offer(img);
        }
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

        BufferedImage canvas = getCanvasFromPool(canvasW, canvasH);
        java.awt.Graphics2D g2 = canvas.createGraphics();

        // Quality Presets
        String quality = properties.getPreviewQuality(); // Legacy field from object (defaults to Preview)
        // Note: We use getPreviewScale() now to control resolution, which is driven by
        // Visor settings.

        // Use Visor Bitrate setting to control rendering quality/interpolation
        String visorBitrate = properties.getVisorBitrate();
        boolean highQuality = "Alta".equals(visorBitrate) || "Media".equals(visorBitrate);

        boolean isScrubbingFast = currentScrubbingVelocity > 0.5; // > 0.5 frames/ms is approx > 15 fps movement
        boolean adaptiveLowQuality = isScrubbingFast;

        if (highQuality && !adaptiveLowQuality) {
            g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION,
                    "Alta".equals(visorBitrate) ? java.awt.RenderingHints.VALUE_INTERPOLATION_BICUBIC
                            : java.awt.RenderingHints.VALUE_INTERPOLATION_BILINEAR);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_RENDERING, java.awt.RenderingHints.VALUE_RENDER_QUALITY);
        } else {
            g2.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_OFF);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION,
                    java.awt.RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
            g2.setRenderingHint(java.awt.RenderingHints.KEY_RENDERING, java.awt.RenderingHints.VALUE_RENDER_SPEED);
        }

        // Background
        g2.setColor(java.awt.Color.BLACK);
        g2.fillRect(0, 0, canvasW, canvasH);

        // Get clips active at this frame, sorted by track index (descending so lower
        // index draws last/on top)
        // Get clips active at this frame using the new Interval Tree optimization
        // (O(logN + k) instead of O(N))
        List<TimelineClip> activeClips = model.getClipsAt(targetFrame);
        
        // Filter by visible track types (Video only)
        // We still need to filter here because the tree returns all clips at time T regardless of track type
        java.util.List<TimelineClip> videoClips = new java.util.ArrayList<>();
        for (TimelineClip clip : activeClips) {
            // Need to check track type from model
            // But model has trackTypes list.
            if (model.getTrackTypes().size() > clip.getTrackIndex()) {
                 if (model.getTrackTypes().get(clip.getTrackIndex()) == rocky.ui.timeline.TrackControlPanel.TrackType.VIDEO) {
                     videoClips.add(clip);
                 }
            } else {
                 // default video
                 videoClips.add(clip);
            }
        }
        
        // Sort by track index (descending so lower index draws last/on top)
        videoClips.sort((a, b) -> Integer.compare(b.getTrackIndex(), a.getTrackIndex()));

        for (TimelineClip clip : videoClips) {
            MediaSource source = pool.getSource(clip.getMediaSourceId());
            if (source == null)
                continue;

            long frameInClip = targetFrame - clip.getStartFrame();
            long sourceFrame = clip.getSourceFrameAt(frameInClip);
            monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DECODE_START);
            BufferedImage asset = source.getFrame(sourceFrame, forceFullRes);
            monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.CONVERT_START);
            if (asset == null)
                continue;

            monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_START);
            drawAssetOnCanvas(g2, asset, clip, frameInClip, canvasW, canvasH);
        }

        g2.dispose();

        // --- ACES COLOR MANAGEMENT ---
        if (properties.isAcesEnabled() && !isScrubbingFast && highQuality) {
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

        // Centering by default + user offset
        // User x=0, y=0 means centered in project
        double centerX = (canvasW / 2.0) + transform.getX();
        double centerY = (canvasH / 2.0) + transform.getY();

        float opacity = (float) clip.getOpacityAt(frameInClip);

        // Identity Transform Optimization
        if (transform.getRotation() == 0 && transform.getScaleX() == 1.0 && transform.getScaleY() == 1.0 &&
                transform.getX() == 0 && transform.getY() == 0 && fitScale == 1.0 && opacity >= 1.0f) {
            g2.drawImage(asset, (canvasW - assetW) / 2, (canvasH - assetH) / 2, null);
            return;
        }

        java.awt.geom.AffineTransform at = new java.awt.geom.AffineTransform();
        at.translate(centerX, centerY);
        at.rotate(Math.toRadians(transform.getRotation()));
        at.scale(finalScaleX, finalScaleY);
        // Anchor point (default center of the image)
        at.translate(-assetW * transform.getAnchorX(), -assetH * transform.getAnchorY());

        java.awt.Composite oldComp = g2.getComposite();
        if (opacity < 1.0f) {
            g2.setComposite(
                    java.awt.AlphaComposite.getInstance(java.awt.AlphaComposite.SRC_OVER, Math.max(0.0f, opacity)));
        }

        g2.drawImage(asset, at, null);

        if (opacity < 1.0f) {
            g2.setComposite(oldComp);
        }
    }
}
