package egine.engine;

import b.timeline.TimelineClip;
import b.timeline.TimelinePanel;
import egine.media.MediaPool;
import egine.media.MediaSource;
import java.util.List;
import java.awt.image.BufferedImage;

/**
 * The logic that determines what to show on the visor based on playhead position.
 */
public class FrameServer {
    private TimelinePanel timeline;
    private MediaPool pool;
    private a.visor.VisualizerPanel visualizer;
    private b.timeline.ProjectProperties properties;
    private final java.util.concurrent.ExecutorService executor = java.util.concurrent.Executors.newSingleThreadExecutor();
    private long lastSubmittedFrame = -1;

    public FrameServer(TimelinePanel timeline, MediaPool pool, a.visor.VisualizerPanel visualizer) {
        this.timeline = timeline;
        this.pool = pool;
        this.visualizer = visualizer;
    }

    public void setProperties(b.timeline.ProjectProperties props) {
        this.properties = props;
    }

    public TimelinePanel getTimeline() { return timeline; }

    public void processFrame(double timeInSeconds) {
        long targetFrame = (long) (timeInSeconds * 30); // Assuming 30 FPS
        
        // Skip if already processing or processed
        if (targetFrame == lastSubmittedFrame) return;
        lastSubmittedFrame = targetFrame;

        // Offload decoding to a background thread to keep EDT (UI) responsive
        executor.submit(() -> {
            BufferedImage img = getFrameAt(targetFrame);
            
            if (img != null && properties != null && properties.isLowResPreview()) {
                // Downscale to 480x270 (Proxy)
                int proxyW = 480;
                int proxyH = 270;
                BufferedImage proxy = new BufferedImage(proxyW, proxyH, BufferedImage.TYPE_INT_RGB);
                java.awt.Graphics2D g2 = proxy.createGraphics();
                g2.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);
                g2.drawImage(img, 0, 0, proxyW, proxyH, null);
                g2.dispose();
                img = proxy;
            }
            
            final BufferedImage finalImg = img;
            javax.swing.SwingUtilities.invokeLater(() -> {
                visualizer.updateFrame(finalImg);
            });
        });
    }

    public BufferedImage getFrameAt(long targetFrame) {
        List<TimelineClip> allClips = timeline.getClips();
        
        TimelineClip activeClip = null;
        for (TimelineClip clip : allClips) {
            if (targetFrame >= clip.getStartFrame() && targetFrame < (clip.getStartFrame() + clip.getDurationFrames())) {
                // Check if track is VIDEO
                if (timeline.getTrackType(clip.getTrackIndex()) == b.timeline.TrackControlPanel.TrackType.VIDEO) {
                    // Layering: Lowest track index is "on top" (Vegas/Premiere standard)
                    if (activeClip == null || clip.getTrackIndex() < activeClip.getTrackIndex()) {
                        activeClip = clip;
                    }
                }
            }
        }

        if (activeClip != null) {
            String mediaId = activeClip.getMediaSourceId();
            MediaSource source = pool.getSource(mediaId);
            
            if (source != null) {
                long frameInClip = targetFrame - activeClip.getStartFrame();
                long sourceFrame = activeClip.getSourceOffsetFrames() + frameInClip;
                return source.getFrame(sourceFrame);
            }
        }
        return null; // Black or empty frame
    }
}
