package rocky.core.engine;

import rocky.core.model.TimelineClip;
import rocky.core.model.ClipTransform;
import rocky.core.logic.TemporalMath;
import rocky.ui.timeline.TimelinePanel;
import rocky.core.media.MediaPool;
import rocky.core.media.MediaSource;
import java.util.List;
import java.awt.image.BufferedImage;
import java.awt.Graphics2D;
import rocky.core.plugins.AppliedPlugin;
import rocky.core.plugins.PluginManager;
import rocky.core.plugins.RockyEffect;
import rocky.core.plugins.RockyTransition;
import rocky.core.plugins.RockyMediaGenerator;

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
    private final java.util.concurrent.atomic.AtomicLong lastShownFrame = new java.util.concurrent.atomic.AtomicLong(-1);
    private final java.util.concurrent.atomic.AtomicLong totalRequests = new java.util.concurrent.atomic.AtomicLong(0);
    private BufferedImage currentVisibleBuffer = null;
    private long lastRequestTime = 0;
    private double currentScrubbingVelocity = 0; // frames per ms
    private final int MAX_POOL_SIZE = 100; // Increased for high core counts and deep pipelining

    // --- OPTIMIZATION: List and Object Pooling to reduce GC ---
    private final java.util.concurrent.ConcurrentLinkedQueue<java.util.ArrayList<TimelineClip>> clipListPool = new java.util.concurrent.ConcurrentLinkedQueue<>();
    private final ClipTransform reusableTransform = new ClipTransform();

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
        
        // --- SAFE RECYCLE INTEGRATION ---
        this.visualizer.setRecycleCallback(img -> returnCanvasToPool(img));
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
            // 1. Revision and Sync Check
            if (model.getLayoutRevision() > taskRevision) {
                return;
            }

            long target = latestTargetFrame.get();
            if (target != -1 && !isPrefetch) {
                // SYNC SENTRY: Adaptive drop threshold (more lenient at higher FPS)
                int dropThreshold = (properties != null && properties.getFPS() > 50) ? 6 : 4;
                if (Math.abs(target - frame) > dropThreshold) {
                    monitor.incrementDroppedFrames(); // Telemetry
                    return; // Drop if too late
                }
                
                if (latestTargetFrame.get() != frame)
                    return;
            }

            if (!isPrefetch) {
                monitor.startFrame();
                monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.SEEK_START);
            }

            // 2. Render logic
            BufferedImage rendered;
            try {
                rendered = getFrameAt(frame, false);
            } catch (Exception e) {
                e.printStackTrace();
                return;
            }

            // 3. Post-Render Sync Check
            long postTarget = latestTargetFrame.get();
            if (!isPrefetch && Math.abs(postTarget - frame) > 1) {
                // If it took too long to render and we already moved on, don't update UI
                frameCache.put(frame, rendered);
                monitor.incrementDecoderStalls(); // Telemetry
                return;
            }

            frameCache.put(frame, rendered);
            manageCacheSize(frame);

            if (!isPrefetch) {
                // ASYNC TEXTURE UPLOAD
                visualizer.prepareVramFrame(rendered);

                monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_START);
                javax.swing.SwingUtilities.invokeLater(() -> {
                    // FINAL SYNC CHECK: Ensure we are not showing a stale/out-of-order frame
                    long currentTarget = latestTargetFrame.get();
                    long shown = lastShownFrame.get();
                    
                    // Logic: If the frame is older than what's on screen, only allow it if 
                    // we are scrubbing/seeking (indicated by a large gap between current target and shown frame)
                    if (frame < shown && Math.abs(currentTarget - shown) < 20) {
                        return; // Block jitter
                    }
                    
                    lastShownFrame.set(frame);
                    currentVisibleBuffer = rendered;
                    visualizer.updateFrame(rendered);
                    monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_END);
                    monitor.endFrame();
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
        if (monitor != null) {
            monitor.setTargetFPS(props.getFPS());
        }
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
        double projectFPS = (properties != null) ? properties.getFPS() : 30.0;
        double visorFPS = (properties != null) ? properties.getVisorFPS() : projectFPS;
        long targetFrame = Math.round(timeInSeconds * projectFPS);

        // --- VISOR FPS THROTTLING ---
        // If we want lower preview fluidity than project FPS, we skip some frames here
        if (!force && visorFPS < projectFPS) {
            long visorMod = Math.round(projectFPS / visorFPS);
            if (visorMod > 1 && totalRequests.get() % visorMod != 0) {
                totalRequests.incrementAndGet();
                return;
            }
        }
        totalRequests.incrementAndGet();

        if (force) {
            BufferedImage removed = frameCache.remove(targetFrame);
            if (removed != null)
                returnCanvasToPool(removed);
        } else if (frameCache.containsKey(targetFrame)) {
            BufferedImage cached = frameCache.get(targetFrame);
            visualizer.prepareVramFrame(cached);
            visualizer.updateFrame(cached);
            prefetchFrames(targetFrame);
            return;
        } else {
            monitor.incrementCacheMisses(); // Telemetry
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

        // --- QUEUE MANAGEMENT ---
        // If the queue is too deep (> 5 pending frames), purge prefetch tasks of the same revision
        if (executor.getQueue().size() > 5) {
            // Custom cleanup logic could go here, but PriorityBlockingQueue handles priority.
            // However, we can track and skip prefetch tasks if needed.
        }

        executor.execute(new RenderTask(targetFrame, false, model.getLayoutRevision()));
        
        // --- SMART LOOK-AHEAD ---
        // Only prefetch if scrubbing is slow or we are playing (vel approx 0 or steady 1x)
        if (currentScrubbingVelocity < 1.0) {
            prefetchFrames(targetFrame);
        }
    }

    private void prefetchFrames(long centerFrame) {
        double fps = (properties != null) ? properties.getFPS() : 30.0;
        int radius = (fps > 50) ? 60 : ((fps > 40) ? 40 : 20); // Doubled radius for smoother playback
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
        if (frameCache.size() > maxFrames * 1.5) { // Only clean when significantly over limit
            // Remove frames far away from current
            java.util.List<Long> toRemove = new java.util.ArrayList<>();
            for (Long f : frameCache.keySet()) {
                if (Math.abs(f - currentFrame) > maxFrames) {
                    toRemove.add(f);
                }
            }
            
            for (Long f : toRemove) {
                BufferedImage img = frameCache.remove(f);
                if (img != null && img != currentVisibleBuffer) {
                    returnCanvasToPool(img);
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

        final int fCanvasW = canvasW;
        final int fCanvasH = canvasH;

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
        // Optimization: Use pooled list for query
        java.util.ArrayList<TimelineClip> activeClips = clipListPool.poll();
        if (activeClips == null) activeClips = new java.util.ArrayList<>();
        else activeClips.clear();
        
        model.getClipTree().query(targetFrame, activeClips);
        
        // Filter by visible track types (Video only)
        // We still need to filter here because the tree returns all clips at time T regardless of track type
        // Filter by visible track types (Video only)
        // Use pooling to avoid new ArrayList creation
        java.util.ArrayList<TimelineClip> videoClips = clipListPool.poll();
        if (videoClips == null) videoClips = new java.util.ArrayList<>();
        else videoClips.clear();

        for (TimelineClip clip : activeClips) {
            if (model.getTrackTypes().size() > clip.getTrackIndex()) {
                 if (model.getTrackTypes().get(clip.getTrackIndex()) == rocky.ui.timeline.TrackControlPanel.TrackType.VIDEO) {
                     videoClips.add(clip);
                 }
            } else {
                 videoClips.add(clip);
            }
        }
        
        // Sort by track index (descending so lower index draws last/on top)
        // Optimization: Skip sort if only one clip
        if (videoClips.size() > 1) {
            videoClips.sort((a, b) -> Integer.compare(b.getTrackIndex(), a.getTrackIndex()));
        }

        // Start measuring Decode time (Aggregate for all clips)
        monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DECODE_START);

        // 1. Identify all clips needed for this frame (Normal + Transition neighbors)
        java.util.Set<TimelineClip> allNeededClips = new java.util.HashSet<>(videoClips);
        for (TimelineClip clip : videoClips) {
            if (properties.isPluginsEnabled() && clip.getFadeInTransition() != null && targetFrame - clip.getStartFrame() < clip.getFadeInFrames()) {
                TimelineClip clipA = findOverlappingOutgoingClip(clip, targetFrame);
                if (clipA != null) allNeededClips.add(clipA);
            }
        }

        // 2. Parallel Decode ALL needed clips
        java.util.Map<TimelineClip, BufferedImage> assets = allNeededClips.parallelStream().collect(
            java.util.stream.Collectors.toConcurrentMap(
                clip -> clip,
                clip -> {
                    MediaSource source = pool.getSource(clip.getMediaSourceId());
                    if (source == null && clip.getMediaGenerator() == null) return null;

                    if (source != null) {
                        rocky.core.media.DecoderPool.touch(source.getFilePath());
                    }

                    long frameInClip = targetFrame - clip.getStartFrame();
                    long sourceFrame = TemporalMath.getSourceFrameAt(clip, frameInClip);
                    
                    if (clip.getMediaGenerator() != null) {
                        BufferedImage genAsset = getCanvasFromPool(fCanvasW, fCanvasH);
                        Graphics2D g2gen = genAsset.createGraphics();
                        AppliedPlugin genInfo = clip.getMediaGenerator();
                        if (genInfo.getPluginInstance() == null) {
                            genInfo.setPluginInstance(PluginManager.getInstance().getGenerator(genInfo.getPluginName()));
                        }
                        if (genInfo.getPluginInstance() instanceof RockyMediaGenerator) {
                            ((RockyMediaGenerator) genInfo.getPluginInstance()).generate(g2gen, fCanvasW, fCanvasH, frameInClip, genInfo.getParameters());
                        }
                        g2gen.dispose();
                        return genAsset;
                    } else {
                        return source.getFrame(sourceFrame, forceFullRes);
                    }
                },
                (u, v) -> u
            )
        );

        monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.CONVERT_START);

        // 3. Sequential Composition
        for (TimelineClip clip : videoClips) {
            BufferedImage asset = assets.get(clip);
            if (asset == null) continue;

            long frameInClip = targetFrame - clip.getStartFrame();
            
            // --- TRANSITION HANDLING ---
            AppliedPlugin fadeInTrans = clip.getFadeInTransition();
            if (properties.isPluginsEnabled() && fadeInTrans != null && frameInClip < clip.getFadeInFrames()) {
                TimelineClip clipA = findOverlappingOutgoingClip(clip, targetFrame);
                BufferedImage assetA = (clipA != null) ? assets.get(clipA) : null;
                
                if (assetA != null) {
                    RockyTransition trans = PluginManager.getInstance().getTransition(fadeInTrans.getPluginName());
                    if (trans != null) {
                        float progress = (float) frameInClip / clip.getFadeInFrames();
                        trans.render(g2, canvasW, canvasH, assetA, asset, progress, fadeInTrans.getParameters());
                        
                        // Cleanup generator asset if needed
                        if (clip.getMediaGenerator() != null) returnCanvasToPool(asset);
                        continue; 
                    }
                }
            }

            drawAssetOnCanvas(g2, asset, clip, frameInClip, canvasW, canvasH);
            
            // Cleanup generator asset if needed
            if (clip.getMediaGenerator() != null) {
                returnCanvasToPool(asset);
            }
        }
        
        // Mark for DRAW_START (composition finished)
        monitor.mark(rocky.core.diagnostics.PerformanceMonitor.Mark.DRAW_START);
        
        g2.dispose();
        
        // RECYCLE ALL LISTS
        if (clipListPool.size() < 10) {
            clipListPool.offer(activeClips);
            clipListPool.offer(videoClips);
        }

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
        
        BufferedImage renderAsset = asset;
        BufferedImage pooledBuffer = null;

        // 1. Uniform Scale to fit project if requested (Aspect Ratio preservation)
        double fitScale = Math.min((double) canvasW / assetW, (double) canvasH / assetH);

        // 2. Apply Custom Transform (Interpolated if keyframes exist)
        // Optimization: Use in-place interpolation to avoid object creation
        TemporalMath.getInterpolatedTransform(clip, frameInClip, reusableTransform);
        double finalScaleX = fitScale * reusableTransform.getScaleX();
        double finalScaleY = fitScale * reusableTransform.getScaleY();

        // Centering by default + user offset
        // User x=0, y=0 means centered in project
        double centerX = (canvasW / 2.0) + reusableTransform.getX();
        double centerY = (canvasH / 2.0) + reusableTransform.getY();

        float opacity = (float) TemporalMath.getOpacityAt(clip, frameInClip);

        // Identity Transform Optimization
        // (Modified to skip if effects exist, as effects need processing)
        if (clip.getAppliedEffects().isEmpty() && reusableTransform.getRotation() == 0 && reusableTransform.getScaleX() == 1.0 && reusableTransform.getScaleY() == 1.0 &&
                reusableTransform.getX() == 0 && reusableTransform.getY() == 0 && fitScale == 1.0 && opacity >= 1.0f) {
            g2.drawImage(asset, (canvasW - assetW) / 2, (canvasH - assetH) / 2, null);
            return;
        }

        // --- PLUGIN EFFECTS (Optimized with Buffer Pooling) ---
        if (properties.isPluginsEnabled() && !clip.getAppliedEffects().isEmpty()) {
            // Apply effects to the asset before drawing
            // Use pooled buffer instead of allocating new BufferedImage every frame
            pooledBuffer = getCanvasFromPool(assetW, assetH);
            Graphics2D eg2 = pooledBuffer.createGraphics();
            eg2.drawImage(asset, 0, 0, null);
            
            synchronized(clip.getAppliedEffects()) {
                for (AppliedPlugin applied : clip.getAppliedEffects()) {
                    RockyEffect effect = PluginManager.getInstance().getEffect(applied.getPluginName());
                    if (effect != null) {
                        try {
                            effect.apply(pooledBuffer, eg2, applied.getParameters());
                        } catch (Exception e) {
                            System.err.println("[FrameServer] Error applying effect " + applied.getPluginName() + ": " + e.getMessage());
                        }
                    }
                }
            }
            eg2.dispose();
            renderAsset = pooledBuffer;
        }

        java.awt.geom.AffineTransform at = new java.awt.geom.AffineTransform();
        at.translate(centerX, centerY);
        at.rotate(Math.toRadians(reusableTransform.getRotation()));
        at.scale(finalScaleX, finalScaleY);
        // Anchor point (default center of the image)
        at.translate(-assetW * reusableTransform.getAnchorX(), -assetH * reusableTransform.getAnchorY());

        java.awt.Composite oldComp = g2.getComposite();
        if (opacity < 1.0f) {
            g2.setComposite(
                    java.awt.AlphaComposite.getInstance(java.awt.AlphaComposite.SRC_OVER, Math.max(0.0f, opacity)));
        }

        g2.drawImage(renderAsset, at, null);

        if (opacity < 1.0f) {
            g2.setComposite(oldComp);
        }
        
        // RECYCLE BUFFER
        if (pooledBuffer != null) {
            returnCanvasToPool(pooledBuffer);
        }
    }

    private TimelineClip findOverlappingOutgoingClip(TimelineClip incomingClip, long targetFrame) {
        // Optimization: Use IntervalTree instead of iterating over all clips
        List<TimelineClip> activeAtFrame = model.getClipsAt(targetFrame);
        for (TimelineClip other : activeAtFrame) {
            if (other == incomingClip) continue;
            if (other.getTrackIndex() == incomingClip.getTrackIndex()) {
                // Since it's active at targetFrame, it already overlaps or contains it
                // We just need to ensure it's on the same track
                return other;
            }
        }
        return null;
    }
}
